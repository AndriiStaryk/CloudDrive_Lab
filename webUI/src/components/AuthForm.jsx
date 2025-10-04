import React, { useState } from 'react';
import { useAuth } from '../hooks/useAuth';

export default function AuthForm() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login, signup } = useAuth();

  const handleAction = async (action) => {
    try {
      setError('');
      await action(username, password);
    } catch (err) {
      setError(err.response?.data?.detail || 'An unexpected error occurred.');
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-form">
        <h1 className="auth-title">Cloud Drive</h1>
        <p className="auth-subtitle">Sign in to your account</p>
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Username"
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
        />
        {error && <p className="auth-error">{error}</p>}
        <button className="btn-primary" onClick={() => handleAction(login)}>Login</button>
        <button className="btn-secondary" onClick={() => handleAction(signup)}>Sign Up</button>
      </div>
    </div>
  );
}