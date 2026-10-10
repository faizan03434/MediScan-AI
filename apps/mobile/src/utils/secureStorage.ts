import { Platform } from 'react-native';
import * as NativeSecureStore from 'expo-secure-store';

// Browser preview keeps tokens only for this tab session; native uses encrypted storage.
export const getItemAsync = async (key: string): Promise<string | null> =>
  Platform.OS === 'web' ? (typeof sessionStorage === 'undefined' ? null : sessionStorage.getItem(key))
    : NativeSecureStore.getItemAsync(key);
export const setItemAsync = async (key: string, value: string): Promise<void> => {
  if (Platform.OS === 'web') sessionStorage.setItem(key, value);
  else await NativeSecureStore.setItemAsync(key, value);
};
export const deleteItemAsync = async (key: string): Promise<void> => {
  if (Platform.OS === 'web') sessionStorage.removeItem(key);
  else await NativeSecureStore.deleteItemAsync(key);
};
