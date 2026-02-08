import React, { useState, useReducer, useRef, useContext } from 'react';

const ThemeContext = React.createContext('light');

function themeReducer(state, action) {
  switch (action.type) {
    case 'toggle':
      return state === 'light' ? 'dark' : 'light';
    default:
      return state;
  }
}

function ThemeToggle() {
  const theme = useContext(ThemeContext);
  return <button>Current Theme: {theme}</button>;
}

function UserProfile() {
  const [user, setUser] = useState({ name: 'John', age: 30 });
  const [theme, dispatch] = useReducer(themeReducer, 'light');
  const inputRef = useRef(null);

  const handleUpdate = () => {
    if (inputRef.current) {
      setUser(prev => ({ ...prev, name: inputRef.current.value }));
    }
  };

  return (
    <ThemeContext.Provider value={theme}>
      <div>
        <h3>User: {user.name}</h3>
        <input ref={inputRef} placeholder="New name" />
        <button onClick={handleUpdate}>Update</button>
        <button onClick={() => dispatch({ type: 'toggle' })}>
          Toggle Theme
        </button>
        <ThemeToggle />
      </div>
    </ThemeContext.Provider>
  );
}

export default UserProfile;
