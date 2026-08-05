/*
 * Firebase SDK Mobile App Configuration
 */

import { initializeApp, getApps } from 'firebase/app';
import { getFirestore } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: "AIzaSy_MOCK_KEY_FOR_LOCAL_DEV",
  authDomain: "pqd-classifier.firebaseapp.com",
  projectId: "pqd-classifier",
  storageBucket: "pqd-classifier.appspot.com",
  messagingSenderId: "1234567890",
  appId: "1:1234567890:web:abcdef123456"
};

let app;
if (getApps().length === 0) {
  app = initializeApp(firebaseConfig);
} else {
  app = getApps()[0];
}

export const db = getFirestore(app);
