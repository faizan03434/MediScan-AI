import React from "react";
import { View, Text, ScrollView, TouchableOpacity, Alert, ActivityIndicator, RefreshControl } from "react-native";
import { useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import doctorService from "../../services/doctorService";
import Card from "../../components/common/Card";
import { Colors } from "../../theme/colors";

export default function ConsentsScreen() {
  const router = useRouter();
  const qc = useQueryClient();

  const { data: consents, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ["receivedConsents"],
    queryFn: doctorService.getReceivedConsents,
  });

  const respond = useMutation({
    mutationFn: ({ id, grant }: { id: string; grant: boolean }) =>
      doctorService.respondToConsent(id, grant),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["receivedConsents"] }),
  });

  const revoke = useMutation({
    mutationFn: (id: string) => doctorService.revokeConsent(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["receivedConsents"] }),
  });

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: Colors.bgDark }}>
      <ScrollView
        contentContainerStyle={{ padding: 20, paddingBottom: 40 }}
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={Colors.primary} />}
      >
        <TouchableOpacity onPress={() => router.back()} style={{ marginBottom: 16 }}>
          <Text style={{ color: Colors.primary }}>Back</Text>
        </TouchableOpacity>

        <Text style={{ color: Colors.textPrimary, fontSize: 22, fontWeight: "800", marginBottom: 4 }}>
          Doctor Access Requests
        </Text>
        <Text style={{ color: Colors.textSecondary, fontSize: 13, marginBottom: 20 }}>
          Manage which doctors can view your health scans
        </Text>

        {isLoading ? (
          <ActivityIndicator color={Colors.primary} style={{ marginTop: 40 }} />
        ) : !consents?.length ? (
          <View style={{ alignItems: "center", paddingTop: 40 }}>
            <Text style={{ fontSize: 40 }}>{"<0x1F468>"}</Text>
            <Text style={{ color: Colors.textSecondary, fontSize: 16, marginTop: 12 }}>No consent requests</Text>
          </View>
        ) : (
          consents.map((c) => {
            const isPending = c.status === "Pending";
            const isActive  = c.status === "Granted" && c.isActive;
            const color     = isPending ? Colors.warning : isActive ? Colors.success : Colors.danger;

            return (
              <Card key={c.id} padding={14} style={{ marginBottom: 10 }}>
                <Text style={{ color: Colors.textPrimary, fontWeight: "700", fontSize: 15 }}>
                  Dr. {c.doctorName}
                </Text>
                <Text style={{ color: Colors.textMuted, fontSize: 12 }}>{c.doctorEmail}</Text>

                <View style={{
                  backgroundColor: `${color}20`, borderRadius: 8,
                  paddingHorizontal: 8, paddingVertical: 3,
                  alignSelf: "flex-start", marginTop: 6,
                }}>
                  <Text style={{ color, fontSize: 11, fontWeight: "700" }}>{c.status}</Text>
                </View>

                {c.consentMessage ? (
                  <Text style={{ color: Colors.textSecondary, fontSize: 12, marginTop: 8, lineHeight: 18 }}
                    numberOfLines={2}>&quot;{c.consentMessage}&quot;</Text>
                ) : null}

                <View style={{ flexDirection: "row", gap: 8, marginTop: 12 }}>
                  {isPending && (
                    <>
                      <TouchableOpacity
                        onPress={() => respond.mutate({ id: c.id, grant: false })}
                        style={{ flex: 1, paddingVertical: 10, borderRadius: 10, borderWidth: 1.5, borderColor: Colors.danger, alignItems: "center" }}
                      >
                        <Text style={{ color: Colors.danger, fontWeight: "700" }}>Deny</Text>
                      </TouchableOpacity>
                      <TouchableOpacity
                        onPress={() => respond.mutate({ id: c.id, grant: true })}
                        style={{ flex: 2, paddingVertical: 10, borderRadius: 10, backgroundColor: Colors.success, alignItems: "center" }}
                      >
                        <Text style={{ color: Colors.white, fontWeight: "700" }}>Grant Access</Text>
                      </TouchableOpacity>
                    </>
                  )}
                  {isActive && (
                    <TouchableOpacity
                      onPress={() => Alert.alert("Revoke?", `Remove Dr. ${c.doctorName} access?`, [
                        { text: "Cancel", style: "cancel" },
                        { text: "Revoke", style: "destructive", onPress: () => revoke.mutate(c.id) },
                      ])}
                      style={{ flex: 1, paddingVertical: 10, borderRadius: 10, borderWidth: 1.5, borderColor: Colors.danger, alignItems: "center" }}
                    >
                      <Text style={{ color: Colors.danger, fontWeight: "700" }}>Revoke Access</Text>
                    </TouchableOpacity>
                  )}
                </View>
              </Card>
            );
          })
        )}

        <View style={{ backgroundColor: `${Colors.info}10`, borderRadius: 12, padding: 12, marginTop: 12, borderWidth: 1, borderColor: `${Colors.info}30` }}>
          <Text style={{ color: Colors.info, fontSize: 12, lineHeight: 18 }}>
            HIPAA: You control all access to your data. Any doctor access is logged and audited. You can revoke at any time.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
