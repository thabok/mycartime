import React, { Component } from 'react';
import MainPage from './pages/MainPage';

class App extends Component {

  
  constructor() {
    super();
    this.state = {}
  }
  
  componentDidMount() {}

  render() {
      return (<MainPage/>)
  }
}

export default App;
