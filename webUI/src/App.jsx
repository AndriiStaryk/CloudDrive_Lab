import { useAuth } from './hooks/useAuth';
import AuthForm from './components/AuthForm';
import MainWindow from './components/MainWindow';
import './styles/App.css';

function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div>Loading...</div>; // Or a proper spinner component
  }

  return (
    <div className="App">
      {user ? <MainWindow /> : <AuthForm />}
    </div>
  );
}

export default App;