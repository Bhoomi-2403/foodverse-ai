export const IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

export function validateImage(file, maxMb = 10) {
  if (!file) return 'No file selected.';
  if (!IMAGE_TYPES.includes(file.type)) return 'Please choose a JPEG, PNG or WebP image.';
  if (file.size > maxMb * 1024 * 1024) return `Image is larger than ${maxMb} MB.`;
  return null;
}

export function validateVideo(file, maxMb = 60) {
  if (!file) return 'No file selected.';
  if (!file.type.startsWith('video/')) return 'Please choose a video file (MP4 recommended).';
  if (file.size > maxMb * 1024 * 1024) return `Video is larger than ${maxMb} MB.`;
  return null;
}
