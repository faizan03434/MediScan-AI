import React from 'react';
import { ActivityIndicator, ScrollView, Text, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import scanService from '../../services/scanService';
import ProtectedImage from '../../components/common/ProtectedImage';
import Button from '../../components/common/Button';
import Card from '../../components/common/Card';
import { Colors } from '../../theme/colors';
import { SCAN_MODULES } from '../../types';

export default function ScanRecordScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const client = useQueryClient();
  const { data: scan, isLoading, error } = useQuery({ queryKey: ['scan', id], queryFn: () => scanService.getScan(id) });
  const module = SCAN_MODULES.find(m => m.id === scan?.scanType);
  const { data: history } = useQuery({ queryKey: ['scanHistory', scan?.scanType],
    queryFn: () => scanService.getHistory(scan!.scanType, 1, 50), enabled: !!scan });
  const previous = history?.scans.find(s => s.id !== scan?.id && new Date(s.createdAt) < new Date(scan!.createdAt));
  const [confirmDelete, setConfirmDelete] = React.useState(false);
  const [deleting, setDeleting] = React.useState(false);
  const [deleteError, setDeleteError] = React.useState('');
  return <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}>
    <ScrollView contentContainerStyle={{ padding: 20, gap: 16 }}>
      <Button title="Back to history" variant="outline" onPress={() => router.back()} />
      {isLoading && <ActivityIndicator color={Colors.primary} />}
      {error && <Text style={{ color: Colors.danger }}>Could not load this record. Try again from history.</Text>}
      {scan && <>
        <Text style={{ color: Colors.textPrimary, fontSize: 26, fontWeight: '800' }}>{module?.icon} {module?.title}</Text>
        <Text style={{ color: Colors.textSecondary }}>{new Date(scan.createdAt).toLocaleString()} · {scan.status}</Text>
        <ProtectedImage uri={scan.imageUrl} style={{ width: '100%', aspectRatio: 1, borderRadius: 18 }} />
        <Card><Text style={{ color: Colors.warning, fontWeight: '700' }}>{scan.detectionResult ?? 'No assessment'}</Text>
          <Text style={{ color: Colors.textSecondary, lineHeight: 23, marginTop: 12 }}>{scan.aiRecommendation}</Text></Card>
        {previous && <Button title="Compare with previous photo" onPress={() => router.push({ pathname: '/compare/[scanId]', params: { scanId: scan.id, previousId: previous.id } })} />}
        <Button title="Capture another photo" onPress={() => router.push({ pathname: '/scan/[type]', params: { type: scan.scanType } })} />
        <Button title={confirmDelete ? 'Confirm remove from history' : 'Remove from history'} variant="outline" disabled={deleting} onPress={async () => {
          if (!confirmDelete) { setConfirmDelete(true); return; }
          setDeleting(true);
          try { await scanService.deleteScan(scan.id); await client.invalidateQueries(); router.replace('/(tabs)/history'); }
          catch { setDeleteError('Unable to remove record. Please retry.'); }
          finally { setDeleting(false); }
        }} />
        {confirmDelete && <View><Text style={{ color: Colors.textSecondary }}>This hides the record immediately. Permanent removal follows the server retention policy; backup copies may remain under that policy.</Text>
          <Button title="Cancel" variant="outline" onPress={() => setConfirmDelete(false)} /></View>}
        {!!deleteError && <Text style={{ color: Colors.danger }}>{deleteError}</Text>}
      </>}
    </ScrollView>
  </SafeAreaView>;
}
