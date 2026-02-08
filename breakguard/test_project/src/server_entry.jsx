import React from 'react';
import ReactDOM from 'react-dom';

// Server-side rendering entry point (React 17 style)
function ServerApp() {
  return (
    <React.StrictMode>
      <div>
        <h1>Server Rendered App</h1>
      </div>
    </React.StrictMode>
  );
}

// Using ReactDOM.hydrate (deprecated in React 18)
ReactDOM.hydrate(
  <ServerApp />,
  document.getElementById('root')
);
