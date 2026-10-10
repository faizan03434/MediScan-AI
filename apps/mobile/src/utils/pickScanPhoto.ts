import * as ImagePicker from 'expo-image-picker';

export async function pickScanPhoto(options: { allowsEditing?: boolean } = {}): Promise<string | null> {
  const result = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ['images'],
    allowsMultipleSelection: false,
    allowsEditing: options.allowsEditing ?? true,
    quality: 0.85,
  });
  if (result.canceled) return null;
  const photo = result.assets[0];
  if (!photo?.uri) throw new Error('No photo was selected. Please try again.');
  if (photo.fileSize && photo.fileSize > 10 * 1024 * 1024) {
    throw new Error('Choose a photo smaller than 10 MB.');
  }
  const extension = photo.uri.split('?')[0].split('.').pop()?.toLowerCase();
  if (photo.mimeType && !['image/jpeg', 'image/png', 'image/webp'].includes(photo.mimeType)) {
    throw new Error('Choose a JPEG, PNG or WebP photo. Export HEIC photos as JPEG first.');
  }
  if (extension && ['heic', 'heif', 'gif', 'bmp', 'tiff'].includes(extension)) {
    throw new Error('Choose a JPEG, PNG or WebP photo.');
  }
  return photo.uri;
}
