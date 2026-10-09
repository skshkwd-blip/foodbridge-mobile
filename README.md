# FoodBridge: mobile app + backend

A food-donation platform connecting donors, NGOs and volunteers, with verification
(donor FSSAI licence, NGO registration, volunteer photo ID) approved by an admin.

    backend/            Flask + MySQL API and website (deploys to Render)
    foodbridge-mobile/  Expo (React Native) app for Android and iOS

The backend builds on the original FoodBridge project (a fork of Himani-0405/FoodBridge).
Added here: token login for the mobile app, hashed passwords for every role,
verification + admin page, documents stored in the database, and hosting setup.

## 1. Database (Aiven, free)
1. Sign up at aiven.io and create a service: **MySQL**, plan **Free**.
2. When it is running, open its overview page and note Host, Port, User, Password and Database name.
   (Usually the user is `avnadmin` and the database is `defaultdb`.)
3. Leave the allowed-IP setting at its default (open), because Render's free plan has no fixed IP.

## 2. Backend (Render, free)
1. Create a Render account, then **New > Web Service** and connect this GitHub repo.
2. Settings:
   - Root Directory: `backend`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --workers 2 --timeout 60`
   - Instance type: Free
3. Environment variables:

   | Name | Value |
   |------|-------|
   | MYSQL_HOST | Host from Aiven |
   | MYSQL_PORT | Port from Aiven |
   | MYSQL_USER | User from Aiven |
   | MYSQL_PASSWORD | Password from Aiven |
   | MYSQL_DB | Database name from Aiven |
   | MYSQL_USE_SSL | true |
   | SECRET_KEY | a long random string (`python3 -c "import secrets;print(secrets.token_hex(32))"`) |
   | ADMIN_PASSWORD | a long password only you know |
   | PYTHON_VERSION | 3.12.7 |

4. Deploy. The tables are created automatically on first start.
5. Check `https://YOUR-SERVICE.onrender.com/api/health` shows `{"status": "ok"}`.
6. Admin page: `https://YOUR-SERVICE.onrender.com/admin`

The free plan sleeps after 15 minutes without requests; the first request afterwards takes about a minute.

## 3. Mobile app
    cd foodbridge-mobile
    npm install
    # set BASE at the top of App.js to https://YOUR-SERVICE.onrender.com
    npx expo start        # scan the QR code with Expo Go

## Running the backend on your laptop
    cd backend && pip install -r requirements.txt
    export MYSQL_USER=root MYSQL_PASSWORD=yourpassword MYSQL_DB=food_db SECRET_KEY=anything ADMIN_PASSWORD=anything
    python app.py

## Existing database from before the mobile app?
Run `backend/verification.sql` once on it. A brand-new database does not need it.
