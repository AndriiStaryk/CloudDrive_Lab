import axios from 'axios';

const API_BASE_URL = "http://127.0.0.1:8000";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

// Interceptor to add the auth token to every request
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export const setAuthToken = (token) => {
  if (token) {
    localStorage.setItem('accessToken', token);
  } else {
    localStorage.removeItem('accessToken');
  }
};

// --- Authentication ---
export const signup = (username, password) => apiClient.post('/auth/signup', { username, password });

export const login = (username, password) => {
  // Manual string construction is the most reliable method for this content type
  const body = `grant_type=&username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}&scope=&client_id=&client_secret=`;
  return apiClient.post('/auth/token', body, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });
};

// --- File Operations ---
export const getFiles = () => apiClient.get('/files');

export const uploadFile = (file, onUploadProgress) => {
  const formData = new FormData();
  // CRITICAL FIX: Explicitly set the filename to the base name, ignoring the folder path.
  formData.append('file', file, file.name); 
  return apiClient.post('/files/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
  });
};

export const downloadFile = async (filename) => {
    const response = await apiClient.get(`/files/download/${filename}`, {
        responseType: 'blob',
    });
    // Create a URL for the blob and trigger download
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
};

export const deleteFile = (filename) => apiClient.delete(`/files/delete/${filename}`);

export const renameFile = (oldFilename, newNameBase) => apiClient.put(`/files/rename/${oldFilename}`, { new_name_base: newNameBase });

export const getFileContent = (filename) => apiClient.get(`/files/content/${filename}`);

export const updateFileContent = (filename, content) => {
  const encodedContent = btoa(unescape(encodeURIComponent(content)));
  return apiClient.put(`/files/update/${filename}`, { content: encodedContent });
};

// Expose the apiClient instance so other parts of the app can access its defaults (like baseURL)
export { apiClient };

