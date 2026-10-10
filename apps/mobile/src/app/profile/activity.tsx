import React, { useState } from 'react';
import { ActivityIndicator, ScrollView, Text, View } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { SafeAreaView } from 'react-native-safe-area-context';
import { getAccountActivity } from '../../services/activityService';
import useAuthStore from '../../store/authStore';
import Button from '../../components/common/Button';
import { Colors } from '../../theme/colors';
import { errorMessage } from '../../utils/errorMessage';
import AppHeader from '../../components/common/AppHeader';
import { Redirect, useRouter } from 'expo-router';

export default function AccountActivityScreen() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const userId = useAuthStore(state => state.user?.id);
  const activity = useQuery({ queryKey: ['accountActivity', userId, page],
    queryFn: () => getAccountActivity(page), enabled: !!userId });
  if (!userId) return <Redirect href="/(auth)/login" />;
  return <SafeAreaView edges={['left', 'right', 'bottom']} style={{ flex: 1, backgroundColor: Colors.bgDark }}>
    <AppHeader />
    <ScrollView contentContainerStyle={{ padding: 20, gap: 16, maxWidth: 800, width: '100%', alignSelf: 'center' }}>
      <Button title="Back to profile" variant="outline" onPress={() => router.navigate('/(tabs)/profile')} />
      <Text style={{ color: Colors.textPrimary, fontSize: 24, fontWeight: '700' }}>Account activity</Text>
      <Text style={{ color: Colors.textSecondary }}>Review recorded actions performed through your account. This list includes events recorded by the current development system.</Text>
      {activity.isPending && <ActivityIndicator color={Colors.primary} accessibilityLabel="Loading activity" />}
      {activity.isError && <View style={{ gap: 12 }}><Text style={{ color: Colors.danger }}>{errorMessage(activity.error)}</Text><Button title="Try again" onPress={() => activity.refetch()} /></View>}
      {activity.data?.items.length === 0 && <Text style={{ color: Colors.textSecondary }}>No recorded activity on this page.</Text>}
      {activity.data?.items.map(item => <View key={item.id} style={{ padding: 16, gap: 6, borderRadius: 14, backgroundColor: Colors.bgCard, borderWidth: 1, borderColor: Colors.border }}>
        <Text style={{ color: Colors.textPrimary, fontWeight: '700' }}>{item.action.replace(/[._]/g, ' ')}</Text>
        <Text style={{ color: Colors.textSecondary }}>{item.category} · {item.success ? 'Completed' : 'Unsuccessful'}</Text>
        <Text style={{ color: Colors.textMuted }}>{new Date(item.createdAt).toLocaleString()}</Text>
      </View>)}
      {activity.data && <View style={{ gap: 10 }}>
        <Text style={{ color: Colors.textSecondary }}>{activity.data.totalCount} recorded actions · Page {page}</Text>
        <Button title="Refresh activity" variant="outline" onPress={() => activity.refetch()} />
        {page > 1 && <Button title="Previous page" variant="outline" onPress={() => setPage(value => value - 1)} />}
        {activity.data.hasNextPage && <Button title="Next page" onPress={() => setPage(value => value + 1)} />}
      </View>}
    </ScrollView>
  </SafeAreaView>;
}
