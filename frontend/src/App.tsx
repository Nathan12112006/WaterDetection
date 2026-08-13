import { useEffect, useRef, useState } from 'react'
import './App.css'
import { AppHeader } from './components/AppHeader'
import { ControlsPanel } from './components/ControlsPanel'
import { DetectionSummary } from './components/DetectionSummary'
import { DisabledActionTooltip } from './components/DisabledActionTooltip'
import { ImageGallery } from './components/ImageGallery'
import { ReviewWorkspace } from './components/ReviewWorkspace'
import { EmptyState } from './components/ui/EmptyState'
import {
  VideoWorkspace,
  type VideoWorkspaceHandle,
} from './components/VideoWorkspace'
import { WorkspaceTabs } from './components/WorkspaceTabs'
import { requestDetections } from './lib/api'
import { buildDatasetArchive } from './lib/archive'
import { downloadBlob } from './lib/downloads'
import { createImageEntry, errorText } from './lib/media'
import {
  activeDetections,
  emptyHistory,
  modelReviewDetection,
} from './lib/review'
import type {
  DetectionSettings,
  ImageEntry,
  MediaMode,
  StatusMessage,
  UploadSource,
  WorkspaceTab,
} from './types'

interface VideoSelection {
  file: File
  url: string
}

const INITIAL_SETTINGS: DetectionSettings = {
  uploadSource: 'files',
  model: 'water_detection',
  confidence: 0.25,
  classConfidences: {
    'pipe burst': 0.25,
    'water accumulation': 0.25,
    'water drop': 0.25,
  },
  videoSampleRate: 1,
}

const INITIAL_STATUS: StatusMessage = {
  text: 'Select images or a video to begin.',
  error: false,
}

function effectiveConfidence(settings: DetectionSettings): number {
  return settings.model === 'water_detection'
    ? Math.min(
        settings.classConfidences['pipe burst'],
        settings.classConfidences['water accumulation'],
        settings.classConfidences['water drop'],
      )
    : settings.confidence
}

function resetForDetection(entry: ImageEntry): ImageEntry {
  return {
    ...entry,
    exportDetections: null,
    reviewDetections: null,
    reviewHistory: emptyHistory(),
    reviewViewport: { zoom: 1, panX: 0, panY: 0 },
    reviewSelected: false,
    reviewEdited: false,
    imageApproved: false,
    error: null,
  }
}

function App() {
  const [settings, setSettings] = useState(INITIAL_SETTINGS)
  const [status, setStatus] = useState(INITIAL_STATUS)
  const [mediaMode, setMediaMode] = useState<MediaMode | null>(null)
  const [imageEntries, setImageEntries] = useState<ImageEntry[]>([])
  const [video, setVideo] = useState<VideoSelection | null>(null)
  const [videoRates, setVideoRates] = useState([1])
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('preview')
  const [processing, setProcessing] = useState(false)
  const [resultsVisible, setResultsVisible] = useState(false)
  const [videoSummary, setVideoSummary] = useState<string[]>([])
  const [exporting, setExporting] = useState(false)
  const videoWorkspaceRef = useRef<VideoWorkspaceHandle>(null)
  const objectUrls = useRef(new Set<string>())
  const nextImageId = useRef(1)
  const nextReviewId = useRef(1)

  const reportStatus = (text: string, error = false) =>
    setStatus({ text, error })

  const clearMedia = () => {
    objectUrls.current.forEach((url) => URL.revokeObjectURL(url))
    objectUrls.current.clear()
    setImageEntries([])
    setVideo(null)
    setMediaMode(null)
    setVideoRates([1])
    setActiveTab('preview')
    setResultsVisible(false)
    setVideoSummary([])
  }

  useEffect(
    () => () => {
      objectUrls.current.forEach((url) => URL.revokeObjectURL(url))
    },
    [],
  )

  const updateSettings = (next: DetectionSettings) => {
    if (next.uploadSource !== settings.uploadSource) {
      clearMedia()
      reportStatus(
        next.uploadSource === 'folder'
          ? 'Select a folder of images to begin.'
          : 'Select images or a video to begin.',
      )
    }
    setSettings(next)
  }

  const loadImages = async (files: File[], skipped = 0) => {
    const entries: ImageEntry[] = []
    try {
      for (const file of files) {
        const entry = await createImageEntry(
          file,
          entries.length,
          `image-${nextImageId.current++}`,
        )
        objectUrls.current.add(entry.url)
        entries.push(entry)
      }
      setImageEntries(entries)
      setMediaMode('images')
      setResultsVisible(false)
      reportStatus(
        skipped > 0
          ? `${entries.length} images ready; ${skipped} non-image files skipped.`
          : `${entries.length} image${entries.length === 1 ? '' : 's'} ready to detect.`,
      )
    } catch (error) {
      entries.forEach((entry) => {
        URL.revokeObjectURL(entry.url)
        objectUrls.current.delete(entry.url)
      })
      throw error
    }
  }

  const handleFilesSelected = async (
    files: File[],
    source: UploadSource,
  ) => {
    clearMedia()
    if (files.length === 0) {
      reportStatus(
        source === 'folder'
          ? 'Select a folder of images to begin.'
          : 'Select images or a video to begin.',
      )
      return
    }

    const imageFiles = files.filter((file) => file.type.startsWith('image/'))
    const videoFiles = files.filter((file) => file.type.startsWith('video/'))
    try {
      if (source === 'folder') {
        if (imageFiles.length === 0) {
          throw new Error('The selected folder does not contain images.')
        }
        await loadImages(imageFiles, files.length - imageFiles.length)
        return
      }
      if (videoFiles.length > 0) {
        if (files.length !== 1 || videoFiles.length !== 1) {
          throw new Error(
            'Select either multiple images or one video by itself.',
          )
        }
        const url = URL.createObjectURL(videoFiles[0])
        objectUrls.current.add(url)
        setVideo({ file: videoFiles[0], url })
        setMediaMode('video')
        reportStatus('Loading video metadata…')
        return
      }
      if (imageFiles.length !== files.length) {
        throw new Error('Every selected file must be an image or video.')
      }
      await loadImages(imageFiles)
    } catch (error) {
      clearMedia()
      reportStatus(errorText(error, 'The media could not be loaded.'), true)
    }
  }

  const processImages = async () => {
    let working = imageEntries.map(resetForDetection)
    setImageEntries(working)
    setActiveTab('preview')
    setResultsVisible(true)
    let failedImages = 0
    let totalDetections = 0

    for (let index = 0; index < working.length; index += 1) {
      const entry = working[index]
      reportStatus(
        `Analyzing image ${index + 1} of ${working.length}: ${entry.file.name}`,
      )
      try {
        const detections = await requestDetections({
          media: entry.file,
          filename: entry.file.name,
          model: settings.model,
          confidence: effectiveConfidence(settings),
          classConfidences: settings.classConfidences,
        })
        const reviewDetections = detections.map((detection) =>
          modelReviewDetection(detection, nextReviewId.current++),
        )
        working[index] = {
          ...entry,
          exportDetections: activeDetections(reviewDetections),
          reviewDetections,
        }
        totalDetections += detections.length
      } catch (error) {
        failedImages += 1
        working[index] = {
          ...entry,
          error: errorText(error, 'Detection request failed.'),
        }
      }
      working = [...working]
      setImageEntries(working)
    }

    if (failedImages > 0) {
      reportStatus(
        `${working.length - failedImages} of ${working.length} images completed; ${failedImages} failed.`,
        true,
      )
    } else {
      reportStatus(
        `${working.length} image${working.length === 1 ? '' : 's'} completed with ${totalDetections} total detection${totalDetections === 1 ? '' : 's'}.`,
      )
    }
  }

  const runDetection = async () => {
    if (!mediaMode) {
      reportStatus('Select images or a video first.', true)
      return
    }
    setProcessing(true)
    reportStatus('Starting detection. The first request may load the model.')
    try {
      if (mediaMode === 'images') {
        await processImages()
      } else {
        const result = await videoWorkspaceRef.current?.analyze({
          model: settings.model,
          confidence: effectiveConfidence(settings),
          classConfidences: settings.classConfidences,
          sampleRate: settings.videoSampleRate,
        })
        if (!result) throw new Error('Video preview is unavailable.')
        setVideoSummary(result.summary)
        setResultsVisible(true)
        reportStatus(
          `Video analysis completed with ${result.persistentTracks} persistent region${result.persistentTracks === 1 ? '' : 's'}.`,
        )
      }
    } catch (error) {
      reportStatus(errorText(error, 'Detection request failed.'), true)
    } finally {
      setProcessing(false)
    }
  }

  const reviewEnabled = imageEntries.some(
    (entry) => entry.reviewDetections !== null,
  )

  const visibleTab =
    activeTab === 'review' && reviewEnabled ? 'review' : 'preview'

  const exportableEntries = imageEntries.filter(
    (entry) => entry.exportDetections !== null,
  )

  const exportDataset = async () => {
    if (exportableEntries.length === 0) {
      reportStatus('Run image detection before exporting a dataset.', true)
      return
    }
    setExporting(true)
    try {
      const archive = await buildDatasetArchive(exportableEntries)
      downloadBlob(archive, 'water-leak-yolo-dataset.zip')
      reportStatus(
        `Dataset ZIP created with ${exportableEntries.length} images.`,
      )
    } catch (error) {
      reportStatus(errorText(error, 'Dataset export failed.'), true)
    } finally {
      setExporting(false)
    }
  }

  return (
    <main className="app-shell">
      <AppHeader
        mediaMode={mediaMode}
        imageCount={imageEntries.length}
        processing={processing}
      />

      <div
        className={`layout${visibleTab === 'review' ? ' review-mode' : ''}`}
      >
        {visibleTab !== 'review' && (
          <ControlsPanel
            settings={settings}
            mediaMode={mediaMode}
            processing={processing}
            status={status}
            videoRates={videoRates}
            onSettingsChange={updateSettings}
            onFilesSelected={(files, source) =>
              void handleFilesSelected(files, source)
            }
            onSubmit={() => void runDetection()}
          />
        )}

        <section className="panel stage" aria-label="Detection preview">
          <WorkspaceTabs
            activeTab={visibleTab}
            mediaMode={mediaMode}
            reviewEnabled={reviewEnabled}
            onTabChange={setActiveTab}
          />
          <div className="stage-content">
            <div id="preview-workspace" hidden={visibleTab !== 'preview'}>
              {mediaMode === null && (
                <EmptyState
                  id="empty-state"
                  title="No media selected"
                  icon={
                    <div className="empty-icon" aria-hidden="true">
                      <svg viewBox="0 0 24 24">
                        <path d="M12 3.5s-5 5.4-5 9.3a5 5 0 0 0 10 0c0-3.9-5-9.3-5-9.3Z" />
                        <path d="M9.7 14.2a2.6 2.6 0 0 0 2.1 1.3" />
                      </svg>
                    </div>
                  }
                >
                  Add photos or a video to preview them here.
                </EmptyState>
              )}
              {mediaMode === 'images' && (
                <ImageGallery
                  entries={imageEntries}
                  canExportDataset={exportableEntries.length > 0}
                  exporting={exporting}
                  onExportDataset={() => void exportDataset()}
                  onStatus={reportStatus}
                />
              )}
              {mediaMode === 'video' && video && (
                <VideoWorkspace
                  ref={videoWorkspaceRef}
                  file={video.file}
                  url={video.url}
                  onRatesChange={(rates) => {
                    setVideoRates(rates)
                    setSettings((current) => ({
                      ...current,
                      videoSampleRate: rates.includes(
                        current.videoSampleRate,
                      )
                        ? current.videoSampleRate
                        : (rates.at(-1) ?? 1),
                    }))
                  }}
                  onStatus={reportStatus}
                />
              )}
            </div>
            <div id="review-workspace" hidden={visibleTab !== 'review'}>
              <ReviewWorkspace
                entries={imageEntries}
                onEntriesChange={setImageEntries}
                onStatus={reportStatus}
              />
            </div>
          </div>
        </section>
      </div>

      {resultsVisible && mediaMode === 'video' && (
        <DetectionSummary items={videoSummary} />
      )}
      <DisabledActionTooltip />
    </main>
  )
}

export default App
