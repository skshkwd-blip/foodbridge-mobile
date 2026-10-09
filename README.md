# FoodBridge mobile app (donor / NGO / volunteer) with verification

    backend/mobile_auth.py     token login for the app (works with your existing routes)
    backend/verification.py    FSSAI / NGO / volunteer ID uploads + admin approval page
    backend/verification.sql   new database columns (run once)
    mobile/App.js              the Expo app

## 1. Backend (PythonAnywhere)
1. Upload `mobile_auth.py` and `verification.py` next to your `app.py`.
2. Bash console: `pip install --user pyjwt`
3. Run `verification.sql` once (Databases tab -> your database -> Mysql console).
   Existing NGO/volunteer test accounts stay locked until verified; the last two lines of the file unlock them.
4. In `app.py`, right after `mysql.init_app(app)` add:

       from mobile_auth import init_mobile_auth
       from verification import init_verification
       init_mobile_auth(app)
       init_verification(app)

5. Web tab -> Environment variables (or top of the WSGI file): set `ADMIN_PASSWORD` to a long password only you know.
6. Also move your MySQL password and `app.secret_key` into environment variables, and change the old password (it is public on GitHub).
7. Reload the web app. Admin page: https://YOURNAME.pythonanywhere.com/admin

## 2. App
    npx create-expo-app foodbridge-mobile --template blank
    cd foodbridge-mobile
    npx expo install @react-native-async-storage/async-storage expo-image-picker

Replace its `App.js` with `mobile/App.js`, set `BASE` at the top, then `npx expo start` and scan the QR code with Expo Go.

## How verification works
- Donor: FSSAI number (14 digits) + certificate photo. Optional for individuals; NGOs see a "verified donor" badge.
- NGO: NGO Darpan ID, contact person, registration certificate. Cannot accept food until an admin approves.
- Volunteer: photo ID, selfie, vehicle number, emergency contact. Cannot take pickups until approved.
  The donor sees the volunteer's photo, vehicle number and ID badge on the donation.
- Uploaded documents are saved in `private_uploads/` (never served publicly) and only the admin page can open them.
