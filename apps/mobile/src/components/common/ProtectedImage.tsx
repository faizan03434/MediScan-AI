import React, { useEffect, useState } from 'react';
import { Image, ImageProps, Platform } from 'react-native';
import api, { resolveImageUrl } from '../../services/api';
import useAuthStore from '../../store/authStore';

export default function ProtectedImage({ uri, ...props }: Omit<ImageProps, 'source'> & { uri?: string }) {
  const token = useAuthStore(s => s.accessToken);
  const url = resolveImageUrl(uri?.replace(/^\/uploads\//, '/api/v1/media/'));
  const [blobUrl, setBlobUrl] = useState<string>();
  useEffect(() => {
    if (Platform.OS !== 'web' || !url) return;
    let active = true;
    let objectUrl: string | undefined;
    setBlobUrl(undefined);
    api.get(url, { responseType: 'blob' }).then(response => {
      if (active) { objectUrl = URL.createObjectURL(response.data); setBlobUrl(objectUrl); }
    }).catch(() => {});
    return () => { active = false; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [url, token]);
  if (!url || (Platform.OS === 'web' && !blobUrl)) return null;
  return <Image {...props} source={Platform.OS === 'web' ? { uri: blobUrl }
    : { uri: url, headers: { Authorization: `Bearer ${token}` } }} />;
}
