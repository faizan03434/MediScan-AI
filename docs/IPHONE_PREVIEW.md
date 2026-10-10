# iPhone preview

For the shared Android/iPhone launcher, see [mobile preview](MOBILE_PREVIEW.md). The generated QR is now `.preview/mobile-qr.png`.

This is an Expo SDK 54 development preview. Install **Expo Go** from the iPhone App Store, as supported by [Expo's compatibility guidance](https://docs.expo.dev/troubleshooting/expo-go-version-mismatch/).

1. Put iPhone and computer on the same Wi-Fi; keep the computer awake.
2. Scan the preview QR using the iPhone Camera, then tap **Open in Expo Go**.
3. Complete the development consent. Use local patient credentials: `patient@mediscan.ai` / `Patient@1234`, or configure SMTP first to register a verified test account (see `AUTH_SETUP.md`).
4. Select a module, accept upload consent, grant camera access, take a photo or choose one from the gallery.
5. View saved records in History. The current output is intentionally **inconclusive**, because medical models are not validated.

The QR encodes a normal **HTTP link** to `/preview`. It opens a handoff page in Safari; tap **Open in Expo Go** there. Medicine package barcodes are a separate scanner inside the Medicines tab.

The launcher generates `.preview/mobile-qr.png` using the current LAN address. A decoded QR and a successful LAN request from this computer do not prove phone permissions or Wi-Fi isolation; verify on the physical iPhone too.

## Start again

From the repository root:

```powershell
dotnet build backend/MediScan.sln
./infrastructure/Start-Preview.ps1
```

The launcher uses API port 5000, internal AI port 8001 and Expo port 8081. It runs background processes with logs under `.preview/`. It reuses existing listeners; after source edits stop the relevant project processes and rebuild/restart so old code is not reused.

For an interactive terminal showing Expo's QR:

```powershell
cd apps/mobile
npx expo start --lan --port 8081
```

If your network IP changes, the QR changes. The native app derives its API host from Expo's LAN address unless `EXPO_PUBLIC_API_URL` is set. Do not set the API URL to `localhost` on a physical phone.

## Connection checks

- From iPhone Safari, open `http://COMPUTER_LAN_IP:5000/api/v1/health`. If unavailable, check same Wi-Fi, client isolation, VPN and Windows Firewall. Allow the project on a trusted private network if Windows prompts.
- Open the LAN link in Expo Go if scanning fails. Allow Expo Go local-network access in iPhone Settings.
- Browser camera tests on a LAN HTTP URL can be blocked by secure-context rules. Use native Expo Go for the iPhone camera and barcode workflow; desktop localhost can test browser photo capture.
- A tunnel for Metro alone does not expose the local API. Do not expect an Expo tunnel QR to make authenticated backend operations work across networks.

## Current limits

Still-photo capture is working plumbing; real-time medical ROI detection is pending. Printed-English OCR and editable confirmation are implemented; local OCR weights must be prepared. Pakistan GTIN mapping and clinical prescription suitability verification remain pending. Local HTTP, seeded accounts and local development storage are unsuitable for real medical data. Phone camera and permissions require actual iPhone testing; computer checks cannot confirm them.
