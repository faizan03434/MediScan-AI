import { Platform } from 'react-native';

export async function appendImage(form: FormData, uri: string) {
  if (Platform.OS === 'web') {
    const response = await fetch(uri);
    const blob = await response.blob();
    form.append('image', blob, `capture.${blob.type === 'image/png' ? 'png' : 'jpg'}`);
  } else {
    const extension = uri.split('?')[0].split('.').pop()?.toLowerCase();
    const type = extension === 'png' ? 'image/png' : extension === 'webp' ? 'image/webp' : 'image/jpeg';
    form.append('image', { uri, name: `capture.${extension ?? 'jpg'}`, type } as unknown as Blob);
  }
}
