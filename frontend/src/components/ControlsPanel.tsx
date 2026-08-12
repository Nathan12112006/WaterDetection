import type { ChangeEvent, FormEvent } from 'react'
import type {
  DetectionSettings,
  MediaMode,
  StatusMessage,
  UploadSource,
} from '../types'
import { ActionButton } from './ui/ActionButton'
import { FormField } from './ui/FormField'

interface ControlsPanelProps {
  settings: DetectionSettings
  mediaMode: MediaMode | null
  processing: boolean
  status: StatusMessage
  videoRates: readonly number[]
  onSettingsChange: (settings: DetectionSettings) => void
  onFilesSelected: (files: File[], source: UploadSource) => void
  onSubmit: () => void
}

function clampConfidence(value: string): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? Math.min(1, Math.max(0, parsed)) : 0
}

export function ControlsPanel({
  settings,
  mediaMode,
  processing,
  status,
  videoRates,
  onSettingsChange,
  onFilesSelected,
  onSubmit,
}: ControlsPanelProps) {
  const update = <Key extends keyof DetectionSettings>(
    key: Key,
    value: DetectionSettings[Key],
  ) => onSettingsChange({ ...settings, [key]: value })

  const handleFiles = (
    event: ChangeEvent<HTMLInputElement>,
    source: UploadSource,
  ) => {
    onFilesSelected(Array.from(event.currentTarget.files ?? []), source)
    event.currentTarget.value = ''
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    onSubmit()
  }

  return (
    <section className="panel controls-panel">
      <form id="detection-form" onSubmit={submit}>
        <div className="form-heading">
          <p className="section-kicker">New analysis</p>
          <h2>Detection setup</h2>
          <p>Choose your media and confidence threshold.</p>
        </div>

        <FormField
          controlId="upload-source"
          label="What do you want to upload?"
        >
          <select
            id="upload-source"
            value={settings.uploadSource}
            onChange={(event) =>
              update(
                'uploadSource',
                event.currentTarget.value as UploadSource,
              )
            }
          >
            <option value="files">Image or video files</option>
            <option value="folder">Folder of images</option>
          </select>
        </FormField>

        <FormField
          id="file-upload-field"
          controlId="media-files"
          label="Upload image or video"
          className="upload-field"
          hidden={settings.uploadSource === 'folder'}
          hint={
            <>
              Multiple images, or one video by itself. Do not mix media types
              in one selection.
            </>
          }
        >
          <input
            id="media-files"
            name="files"
            type="file"
            accept="image/*,video/*"
            multiple
            onChange={(event) => handleFiles(event, 'files')}
          />
        </FormField>

        <FormField
          id="folder-upload-field"
          controlId="folder-files"
          label="Upload folder of images"
          className="upload-field"
          hidden={settings.uploadSource !== 'folder'}
          hint="All supported images in the selected folder will be analyzed."
        >
          <input
            id="folder-files"
            type="file"
            accept="image/*"
            multiple
            {...{ webkitdirectory: '', directory: '' }}
            onChange={(event) => handleFiles(event, 'folder')}
          />
        </FormField>

        <FormField
          controlId="model"
          label="Model"
        >
          <select
            id="model"
            name="model"
            value={settings.model}
            onChange={(event) =>
              update(
                'model',
                event.currentTarget.value as DetectionSettings['model'],
              )
            }
          >
            <option value="water_accumulation">WaterAccumulation</option>
            <option value="water_detection">WaterDetection</option>
          </select>
        </FormField>

        {settings.model === 'water_accumulation' && (
          <FormField
            controlId="confidence-range"
            label={
              <span className="field-label-row">
                Minimum confidence
                <output htmlFor="confidence-range">
                  {Math.round(settings.confidence * 100)}%
                </output>
              </span>
            }
          >
            <div className="confidence-controls">
              <input
                id="confidence-range"
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={settings.confidence}
                onChange={(event) =>
                  update('confidence', clampConfidence(event.currentTarget.value))
                }
              />
              <input
                id="confidence-number"
                name="confidence"
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={settings.confidence}
                onChange={(event) =>
                  update('confidence', clampConfidence(event.currentTarget.value))
                }
              />
            </div>
          </FormField>
        )}

        {settings.model === 'water_detection' && (
          <div className="class-confidence-controls" aria-label="Class confidence thresholds">
            <p className="field-label">Class confidence</p>
            {(['pipe burst', 'water accumulation', 'water drop'] as const).map(
              (className) => {
                const id = `confidence-${className.replaceAll(' ', '-')}`
                return (
                  <FormField
                    key={className}
                    controlId={id}
                    label={
                      <span className="field-label-row">
                        {className}
                        <output htmlFor={id}>
                          {Math.round(settings.classConfidences[className] * 100)}%
                        </output>
                      </span>
                    }
                  >
                    <input
                      id={id}
                      type="range"
                      min="0"
                      max="1"
                      step="0.01"
                      value={settings.classConfidences[className]}
                      onChange={(event) =>
                        update('classConfidences', {
                          ...settings.classConfidences,
                          [className]: clampConfidence(event.currentTarget.value),
                        })
                      }
                    />
                  </FormField>
                )
              },
            )}
          </div>
        )}

        <FormField
          id="video-rate-field"
          controlId="video-sample-rate"
          label="Video samples per second"
          hidden={mediaMode !== 'video'}
          hint={
            <>
              Available rates adjust to the video length. Videos that are too
              long to analyze at 1 FPS are rejected.
            </>
          }
        >
          <select
            id="video-sample-rate"
            value={settings.videoSampleRate}
            onChange={(event) =>
              update('videoSampleRate', Number(event.currentTarget.value))
            }
          >
            {videoRates.map((rate) => (
              <option key={rate} value={rate}>
                {rate} FPS
              </option>
            ))}
          </select>
        </FormField>

        <ActionButton
          id="detect-button"
          type="submit"
          busy={processing}
          busyLabel="Detecting…"
        >
          Run detection <span aria-hidden="true">→</span>
        </ActionButton>
        <p
          id="status"
          className={`status${status.error ? ' error' : ''}`}
          role="status"
          aria-live="polite"
        >
          {status.text}
        </p>
      </form>
    </section>
  )
}
