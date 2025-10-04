import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from '../hooks/useAuth.jsx';
import TopBar from './TopBar';
import FileTable from './FileTable';
import PreviewModal from './PreviewModal';
import * as api from '../api/apiClient.js';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';


export default function MainWindow() {
    const { user } = useAuth();
    const [allFiles, setAllFiles] = useState([]);
    const [selectedFile, setSelectedFile] = useState(null);
    const [filter, setFilter] = useState('all');
    const [loading, setLoading] = useState(true);
    const [previewFile, setPreviewFile] = useState(null);

    const refreshFiles = useCallback(async () => {
        setLoading(true);
        try {
            const response = await api.getFiles();
            setAllFiles(response.data);
        } catch (error) {
            toast.error("Failed to fetch files.");
            console.error(error);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        refreshFiles();
    }, [refreshFiles]);
    
    const handleUpload = async (files) => {
        const uploadPromises = Array.from(files).map(file => {
            const toastId = toast.loading(`Uploading ${file.name}...`);
            return api.uploadFile(file, progressEvent => {
                const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                toast.update(toastId, { render: `Uploading ${file.name}: ${percentCompleted}%`, progress: percentCompleted / 100 });
            }).then(() => {
                toast.success(`${file.name} uploaded successfully!`, { autoClose: 2000 });
                toast.dismiss(toastId);
            }).catch(err => {
                toast.error(`Upload failed for ${file.name}.`);
                toast.dismiss(toastId);
            });
        });

        await Promise.all(uploadPromises);
        refreshFiles();
    };

    const handleDelete = async () => {
        if (!selectedFile) return;
        if (window.confirm(`Are you sure you want to delete ${selectedFile.name}?`)) {
            try {
                await api.deleteFile(selectedFile.name);
                toast.success(`${selectedFile.name} deleted.`);
                refreshFiles();
                setSelectedFile(null);
            } catch (error) {
                toast.error(`Failed to delete ${selectedFile.name}.`);
            }
        }
    };

    const handleDownload = async () => {
        if (!selectedFile) return;
        try {
            toast.info(`Downloading ${selectedFile.name}...`);
            await api.downloadFile(selectedFile.name);
        } catch (error) {
            toast.error(`Failed to download ${selectedFile.name}.`);
        }
    };
    
    const handleRename = async () => {
        if (!selectedFile) return;
        const oldName = selectedFile.name;
        const extension = oldName.includes('.') ? `.${oldName.split('.').pop()}` : '';
        const baseName = extension ? oldName.slice(0, -extension.length) : oldName;
        
        const newBaseName = prompt("Enter new name (without extension):", baseName);

        if (newBaseName && newBaseName !== baseName) {
            try {
                await api.renameFile(oldName, newBaseName);
                toast.success(`Renamed to ${newBaseName}${extension}`);
                refreshFiles();
                setSelectedFile(null);
            } catch (error) {
                toast.error(error.response?.data?.detail || "Rename failed.");
            }
        }
    };

    const handlePreview = (file) => {
      const extension = file.name.split('.').pop().toLowerCase();
      const supportedExtensions = ['c', 'py', 'txt', 'jpg', 'jpeg', 'png'];
      if(supportedExtensions.includes(extension)) {
        setPreviewFile(file);
      } else {
        toast.info("Preview is not available for this file type.");
      }
    };

    const filteredFiles = useMemo(() => {
        if (filter === 'all') return allFiles;
        if (filter === 'py') return allFiles.filter(f => f.name.toLowerCase().endsWith('.py'));
        if (filter === 'img') return allFiles.filter(f => f.name.toLowerCase().match(/\.(jpg|jpeg|png)$/));
        return allFiles;
    }, [allFiles, filter]);

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleUpload(e.dataTransfer.files);
            e.dataTransfer.clearData();
        }
    };
    
    return (
        <div className="main-window" onDragOver={e => e.preventDefault()} onDrop={handleDrop}>
            <ToastContainer position="bottom-right" theme="dark" />
            <div className="header">
              <h3>Cloud Drive</h3>
              <span>Logged in as: <strong>{user.username}</strong></span>
            </div>
            <TopBar
                onUpload={handleUpload}
                onDelete={handleDelete}
                onDownload={handleDownload}
                onRefresh={refreshFiles}
                selectedFile={selectedFile}
                activeFilter={filter}
                onFilterChange={setFilter}
            />
            <FileTable
                files={filteredFiles}
                loading={loading}
                selectedFile={selectedFile}
                onFileSelect={setSelectedFile}
                onFileDoubleClick={handlePreview}
                onRename={handleRename}
                onDelete={handleDelete}
                onDownload={handleDownload}
            />
            <div className="status-bar">
                {selectedFile ? `1 of ${filteredFiles.length} selected` : `${filteredFiles.length} items`}
            </div>
             {previewFile && (
                <PreviewModal
                    file={previewFile}
                    onClose={() => setPreviewFile(null)}
                    onSave={refreshFiles}
                />
            )}
        </div>
    );
}