# Android and iPhone preview

MediScan targets supported Android/iOS devices and a browser preview. Compatibility with every phone/OS version is not verified. Camera/gallery, email login, registration OTP and reset share the same app/backend.

1. Install Expo Go from the Android Play Store or iPhone App Store. Expo Go must support the project's SDK 54; use a development build if the installed store version is incompatible.
2. Connect phone and computer to the same trusted Wi-Fi.
3. Run `dotnet build backend/MediScan.sln` and `./infrastructure/Start-Preview.ps1` from the repository root.
4. Scan `.preview/mobile-qr.png` for a page with Android/iPhone installation links and Expo Go/browser buttons. Android can also scan the Expo terminal QR inside Expo Go; iPhone can use Camera.
5. If Expo Go requests an account, sign in to CLI and Expo Go with the same Expo account. See [Expo's connection instructions](https://docs.expo.dev/get-started/start-developing/).
6. Use test data. Configure SMTP per [auth setup](AUTH_SETUP.md) for real registration/reset emails.

The app derives its API host from Expo's LAN host unless `EXPO_PUBLIC_API_URL` is set. A physical phone cannot reach the computer through `localhost`. Open `http://COMPUTER_LAN_IP:5000/api/v1/health` to check API access; ports 5000 and 8081 must be reachable on the trusted private network.

The launcher reuses existing listeners. After backend/config changes stop the relevant project process and restart the new build. HTTP is only for local preview; real patient use requires production HTTPS/security. Browser camera access requires desktop localhost or HTTPS.

Native Google sign-in needs OAuth configuration and a custom build on both platforms; email works in Expo Go. Physical Android/iPhone camera/barcode/permission validation remains manual. Clinical results remain inconclusive until validated models are approved.
