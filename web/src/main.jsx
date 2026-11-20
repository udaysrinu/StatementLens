// Entry: the whole app re-renders when core.js says its state changed (the old draw()). core reads the
// data from the page's <script id="data"> at import, exactly as the plain-CSS page did.
import React, { useSyncExternalStore } from 'react';
import { createRoot } from 'react-dom/client';
import './tokens.css';
import './app.css';
import * as C from './core.js';
import { Shell } from './Shell.jsx';

function App() {
  useSyncExternalStore(C.subscribe, C.version);
  return <Shell />;
}

createRoot(document.getElementById('root')).render(<App />);
