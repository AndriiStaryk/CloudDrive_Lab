import React, { createContext, useContext, useState, useEffect } from 'react';
import { setAuthToken, login as apiLogin, signup as apiSignup } from '../api/apiClient.js';
import { jwtDecode } from 'jwt-decode';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    try {
      const token = localStorage.getItem('accessToken');
      if (token) {
        const decoded = jwtDecode(token);
        setUser({ username: decoded.sub });
        setAuthToken(token);
      }
    } catch (error) {
      console.error("Invalid token", error);
      setUser(null);
      setAuthToken(null);
    } finally {
        setLoading(false);
    }
  }, []);

  const login = async (username, password) => {
    const response = await apiLogin(username, password);
    const { access_token } = response.data;
    const decoded = jwtDecode(access_token);
    setAuthToken(access_token);
    setUser({ username: decoded.sub });
  };
  
  const signup = async (username, password) => {
    const response = await apiSignup(username, password);
    const { access_token } = response.data;
    const decoded = jwtDecode(access_token);
    setAuthToken(access_token);
    setUser({ username: decoded.sub });
  };

  const logout = () => {
    setUser(null);
    setAuthToken(null);
  };

  const value = { user, loading, login, signup, logout };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  return useContext(AuthContext);
};
