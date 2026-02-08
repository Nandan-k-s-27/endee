import React from 'react';
import ReactDOM from 'react-dom';

function Counter() {
  const [count, setCount] = React.useState(0);
  const [name, setName] = React.useState('BreakGuard');

  React.useEffect(() => {
    document.title = `${name} - Count: ${count}`;
  }, [count, name]);

  const handleClick = React.useCallback(() => {
    setCount(prev => prev + 1);
  }, []);

  const doubleCount = React.useMemo(() => count * 2, [count]);

  return (
    <div>
      <h1>{name}</h1>
      <p>Count: {count} (Double: {doubleCount})</p>
      <button onClick={handleClick}>Increment</button>
    </div>
  );
}

function App() {
  return (
    <React.StrictMode>
      <React.Fragment>
        <Counter />
      </React.Fragment>
    </React.StrictMode>
  );
}

// React 17 style rendering - THIS WILL BREAK IN React 18
ReactDOM.render(<App />, document.getElementById('root'));
