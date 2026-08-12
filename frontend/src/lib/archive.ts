import type { ImageEntry, ReviewDetection } from '../types'
import { MODEL_CLASSES } from '../modelClasses'
import { BoundingBox } from './detections'

const MAX_DATASET_EXPORT_IMAGES = 10_000
const MAX_DATASET_EXPORT_BYTES = 536_870_912

interface ZipEntry {
  name: string
  data: string | Uint8Array
}

function crc32(bytes: Uint8Array): number {
  let crc = 0xffffffff
  for (const byte of bytes) {
    crc ^= byte
    for (let bit = 0; bit < 8; bit += 1) {
      crc = (crc >>> 1) ^ (crc & 1 ? 0xedb88320 : 0)
    }
  }
  return (crc ^ 0xffffffff) >>> 0
}

function writeUint16(bytes: Uint8Array, offset: number, value: number): void {
  new DataView(bytes.buffer).setUint16(offset, value, true)
}

function writeUint32(bytes: Uint8Array, offset: number, value: number): void {
  new DataView(bytes.buffer).setUint32(offset, value, true)
}

function zipDateTime(date: Date): { date: number; time: number } {
  return {
    date:
      ((Math.max(1980, date.getFullYear()) - 1980) << 9) |
      ((date.getMonth() + 1) << 5) |
      date.getDate(),
    time:
      (date.getHours() << 11) |
      (date.getMinutes() << 5) |
      Math.floor(date.getSeconds() / 2),
  }
}

export function createZip(
  entries: readonly ZipEntry[],
  now = new Date(),
): Blob {
  const encoder = new TextEncoder()
  const localParts: ArrayBuffer[] = []
  const centralParts: ArrayBuffer[] = []
  const timestamp = zipDateTime(now)
  let localOffset = 0
  let centralSize = 0

  for (const entry of entries) {
    const name = encoder.encode(entry.name)
    const data =
      typeof entry.data === 'string' ? encoder.encode(entry.data) : entry.data
    const checksum = crc32(data)
    const local = new Uint8Array(30)
    writeUint32(local, 0, 0x04034b50)
    writeUint16(local, 4, 20)
    writeUint16(local, 6, 0x0800)
    writeUint16(local, 10, timestamp.time)
    writeUint16(local, 12, timestamp.date)
    writeUint32(local, 14, checksum)
    writeUint32(local, 18, data.length)
    writeUint32(local, 22, data.length)
    writeUint16(local, 26, name.length)
    localParts.push(
      Uint8Array.from(local).buffer,
      Uint8Array.from(name).buffer,
      Uint8Array.from(data).buffer,
    )

    const central = new Uint8Array(46)
    writeUint32(central, 0, 0x02014b50)
    writeUint16(central, 4, 20)
    writeUint16(central, 6, 20)
    writeUint16(central, 8, 0x0800)
    writeUint16(central, 12, timestamp.time)
    writeUint16(central, 14, timestamp.date)
    writeUint32(central, 16, checksum)
    writeUint32(central, 20, data.length)
    writeUint32(central, 24, data.length)
    writeUint16(central, 28, name.length)
    writeUint32(central, 42, localOffset)
    centralParts.push(
      Uint8Array.from(central).buffer,
      Uint8Array.from(name).buffer,
    )
    centralSize += central.length + name.length
    localOffset += local.length + name.length + data.length
  }

  const end = new Uint8Array(22)
  writeUint32(end, 0, 0x06054b50)
  writeUint16(end, 8, entries.length)
  writeUint16(end, 10, entries.length)
  writeUint32(end, 12, centralSize)
  writeUint32(end, 16, localOffset)
  return new Blob(
    [
      ...localParts,
      ...centralParts,
      Uint8Array.from(end).buffer,
    ],
    {
      type: 'application/zip',
    },
  )
}

function safeFilename(file: File, index: number): string {
  const original = file.name.replace(/[^a-zA-Z0-9._-]+/g, '-')
  return `${String(index + 1).padStart(5, '0')}-${original || `image-${index + 1}.jpg`}`
}

function labelFilename(imageFilename: string): string {
  const extensionIndex = imageFilename.lastIndexOf('.')
  const stem =
    extensionIndex > 0
      ? imageFilename.slice(0, extensionIndex)
      : imageFilename
  return `${stem}.txt`
}

function yoloLabels(
  entry: ImageEntry,
  classIds: ReadonlyMap<string, number>,
): string {
  const lines: string[] = []
  for (const detection of entry.exportDetections ?? []) {
    try {
      const normalized = BoundingBox.from(detection.bbox).toYolo(
        entry.width,
        entry.height,
      )
      lines.push(
        [
          classIds.get(detection.class),
          ...normalized.map((value) => value.toFixed(6)),
        ].join(' '),
      )
    } catch {
      // Invalid reviewed boxes are excluded rather than corrupting the archive.
    }
  }
  return lines.length > 0 ? `${lines.join('\n')}\n` : ''
}

function reviewRecord(detection: ReviewDetection) {
  return {
    class: detection.class,
    bbox: detection.bbox,
    source: detection.source,
    confirmed: detection.confirmed,
    removed: detection.removed,
    modelConfidence:
      detection.source === 'model' ? detection.confidence : null,
  }
}

export async function buildDatasetArchive(
  entries: readonly ImageEntry[],
): Promise<Blob> {
  if (entries.length > MAX_DATASET_EXPORT_IMAGES) {
    throw new Error(
      `Dataset export supports at most ${MAX_DATASET_EXPORT_IMAGES} images.`,
    )
  }
  const estimatedBytes = entries.reduce(
    (total, entry) => total + entry.file.size,
    0,
  )
  if (estimatedBytes > MAX_DATASET_EXPORT_BYTES) {
    throw new Error('The dataset is too large to create in this browser.')
  }

  const classes = [...MODEL_CLASSES]
  const unsupportedClasses = [
    ...new Set(
      entries.flatMap((entry) =>
        (entry.exportDetections ?? [])
          .map((detection) => detection.class)
          .filter((className) => !MODEL_CLASSES.includes(
            className as (typeof MODEL_CLASSES)[number],
          )),
      ),
    ),
  ]
  if (unsupportedClasses.length > 0) {
    throw new Error(
      `Cannot export annotations with unsupported classes: ${unsupportedClasses.join(', ')}.`,
    )
  }
  const classIds = new Map(
    classes.map((className, index) => [className, index]),
  )
  const zipEntries: ZipEntry[] = []
  const reviewRecords: object[] = []
  const validationStartsAt = entries.length >= 2 ? entries.length - 1 : -1

  for (const [index, entry] of entries.entries()) {
    const split =
      entries.length >= 5
        ? (index + 1) % 5 === 0
          ? 'valid'
          : 'train'
        : index === validationStartsAt
          ? 'valid'
          : 'train'
    const filename = safeFilename(entry.file, index)
    zipEntries.push({
      name: `images/${split}/${filename}`,
      data: new Uint8Array(await entry.file.arrayBuffer()),
    })
    zipEntries.push({
      name: `labels/${split}/${labelFilename(filename)}`,
      data: yoloLabels(entry, classIds),
    })
    reviewRecords.push({
      image: `images/${split}/${filename}`,
      approved: entry.imageApproved,
      approvedEmpty:
        entry.imageApproved &&
        (entry.reviewDetections ?? []).every(
          (detection) => detection.removed,
        ),
      annotations: (entry.reviewDetections ?? []).map(reviewRecord),
    })
  }

  const validationPath =
    entries.length >= 2 ? 'images/valid' : 'images/train'
  const yamlNames = classes
    .map((className, index) => `  ${index}: ${JSON.stringify(className)}`)
    .join('\n')
  zipEntries.push({
    name: 'data.yaml',
    data: `path: .\ntrain: images/train\nval: ${validationPath}\nnames:\n${yamlNames}\n`,
  })
  zipEntries.push({
    name: 'README.txt',
    data:
      'This YOLO object-detection dataset contains active reviewed and model-generated annotations.\n' +
      'Unconfirmed model annotations may still require review before training or evaluation.\n' +
      'Images without detections intentionally have empty label files.\n',
  })
  zipEntries.push({
    name: 'review-summary.json',
    data: JSON.stringify({ images: reviewRecords }, null, 2),
  })
  return createZip(zipEntries)
}
