# MediScan email OTP and Google sign-in setup

## Email OTP

The server sends registration and password-reset codes from **iamfaizan884@gmail.com**. Your private `backend/MediScan.API/.env` is ready locally and ignored by Git. Set `Email__Smtp__Password=YOUR_16_CHARACTER_APP_PASSWORD` with spaces removed, then restart the API. Copy `.env.example` to `.env` on a new machine. The API reads it from its content root; real environment variables override it. Values are literal, matching quotes are accepted, and inline comments/interpolation are unsupported. Never put this password in a mobile EXPO_PUBLIC variable.

Alternatively configure private `backend/MediScan.API/appsettings.Local.json`, also ignored by Git. The server `.env` overrides matching JSON settings:

```json
{
  "Email": {
    "From": "iamfaizan884@gmail.com",
    "Smtp": {
      "Host": "smtp.gmail.com",
      "Port": 587,
      "Username": "iamfaizan884@gmail.com",
      "Password": "YOUR_APP_PASSWORD_WITHOUT_SPACES"
    }
  },
  "Authentication": { "Google": { "ClientIds": [] } }
}
```

Enable two-step verification in that Google account, then generate an app password. Paste it only into this local server file, never chat, Git, or an EXPO_PUBLIC variable. Gmail app passwords may be unavailable for some managed accounts. Google guide: https://support.google.com/accounts/answer/185833

Restart the API, then open registration, request a code, and verify the received email. Check spam. Reset uses the same sender. Missing credentials display a configuration message; no account is created without successful verification. Codes expire in 10 minutes, are single-use, allow at most five failed attempts and have a 60-second resend cooldown. Auth endpoints are rate limited. Server memory holds hashed codes and pending password hashes; a restart invalidates pending challenges. Production requires a shared atomic challenge store and managed secrets.

## Google OAuth project

1. Open https://console.cloud.google.com/ and create/select a MediScan project.
2. Configure Google Auth Platform branding, audience and consent. During testing, add your test accounts. Request only basic identity (openid/email/profile).
3. Create an OAuth client of type **Web application**. Add `http://localhost:8081` as an authorized JavaScript origin for local browser testing. Production needs its real HTTPS origin. A plain HTTP LAN IP is not a supported Google web origin; use localhost on the computer for Google testing.
4. Create an OAuth client of type **iOS**, bundle ID `com.mediscan.ai`. Also create an **Android** OAuth client with package `com.mediscan.ai` and the SHA-1 fingerprint of the certificate signing your build. Debug/development and release certificates need their matching registrations.
5. Add both client IDs to the server's `Authentication:Google:ClientIds` array. IDs are public identifiers; no Google client secret is required by this ID-token flow.
6. Create ignored `apps/mobile/.env.local`:

```dotenv
EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID=YOUR_WEB_ID.apps.googleusercontent.com
EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID=YOUR_IOS_ID.apps.googleusercontent.com
```

7. Restart Metro with its cache cleared and restart the API. The browser uses Google's official Identity Services button; the server validates the signature, issuer, audience, expiry and verified email before issuing its own session. Existing email/password accounts must sign in first and use **Profile > Edit Profile > Link Google account** to link the matching Google email.

## Android and iPhone builds

Expo Go supports the current photo preview and email flows. Its binary does not contain the Google native module. Native Google sign-in needs a fresh development build after configuring IDs; `app.config.js` adds the reversed iOS URL scheme automatically.

Android Google sign-in requests a server ID token with the Web client ID; the Android OAuth client authorizes the package/signing certificate and is not passed as an `androidClientId` to this library. Devices need Google Play Services for this flow; email login remains available without them. See [official configuration](https://react-native-google-signin.github.io/docs/setting-up/get-config-file).

Use Expo's development build workflow: Android SDK and `npx expo run:android` for local Android; a Mac with Xcode for local iOS, or EAS Build with your Expo and signing accounts. Native Google sign-in requires a custom build on both platforms, per the [Expo integration guide](https://react-native-google-signin.github.io/docs/setting-up/expo). No physical-phone Google sign-in has been verified yet because OAuth IDs and signed builds have not been supplied.

Official references:
- Google web client setup: https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid
- Google button API: https://developers.google.com/identity/gsi/web/reference/js-reference
- React Native Google Sign In Expo configuration: https://react-native-google-signin.github.io/docs/setting-up/expo

## Verification status

SMTP transport and Google's live identity exchange need your credentials/configuration before an end-to-end test. Automated local tests exercise OTP registration/reset with an in-memory mail capture and real Identity/SQLite password handling; they do not send external mail. This development auth setup is not a HIPAA certification.
