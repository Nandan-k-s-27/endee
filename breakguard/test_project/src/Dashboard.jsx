import React from 'react';
import ReactDOM from 'react-dom';

class Dashboard extends React.Component {
  constructor(props) {
    super(props);
    this.state = { data: null, loading: true };
    this.containerRef = React.createRef();
  }

  componentDidMount() {
    // Using findDOMNode (deprecated in React 18 StrictMode)
    const node = ReactDOM.findDOMNode(this);
    console.log('Dashboard mounted:', node);

    this.setState({ loading: false, data: 'Loaded!' });
  }

  componentWillUnmount() {
    // Using unmountComponentAtNode (deprecated in React 18)
    const portalContainer = document.getElementById('portal');
    if (portalContainer) {
      ReactDOM.unmountComponentAtNode(portalContainer);
    }
  }

  render() {
    const { loading, data } = this.state;

    return (
      <div ref={this.containerRef}>
        <h2>Dashboard</h2>
        {loading ? <p>Loading...</p> : <p>{data}</p>}
        {ReactDOM.createPortal(
          <div>Portal Content</div>,
          document.getElementById('portal') || document.body
        )}
      </div>
    );
  }
}

export default Dashboard;
