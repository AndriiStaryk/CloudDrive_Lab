import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useAuth } from '../hooks/useAuth.jsx';
import TopBar from './TopBar';
import FileTable from './FileTable';
import PreviewModal from './PreviewModal';
import SyncPromptModal from './SyncPromptModal';
import * as api from '../api/apiClient.js';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { LogoutIcon } from '../assets/icons.jsx';

export default function MainWindow() {
    const { user, logout } = useAuth(); // Get logout function from auth hook
    const [allFiles, setAllFiles] = useState([]);
    const [selectedFile, setSelectedFile] = useState(null);
    const [filter, setFilter] = useState('all');
    const [loading, setLoading] = useState(true);
    const [previewFile, setPreviewFile] = useState(null);
    const [isDraggingOver, setIsDraggingOver] = useState(false);
    const [isSyncModalOpen, setIsSyncModalOpen] = useState(false);

    const fileInputRef = useRef(null);
    const folderInputRef = useRef(null);

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
    
    // CRITICAL FIX: Changed to a sequential upload loop to prevent backend concurrency issues.
    const handleUpload = async (files) => {
        for (const file of Array.from(files)) {
             const toastId = toast.loading(`Uploading ${file.name}...`);
            try {
                await api.uploadFile(file, progressEvent => {
                    const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                    toast.update(toastId, { render: `Uploading ${file.name}: ${percentCompleted}%`, progress: percentCompleted / 100 });
                });
                toast.success(`${file.name} uploaded successfully!`, { autoClose: 2000 });
                toast.dismiss(toastId);
            } catch (err) {
                 toast.error(`Upload failed for ${file.name}.`);
                 toast.dismiss(toastId);
                 // Stop the sync process on the first error to avoid further issues
                 break; 
            }
        }
        // Refresh the file list once all uploads are attempted
        refreshFiles();
    };
    
    const handleFileChangeEvent = (event) => {
        if (event.target.files.length > 0) {
            handleUpload(event.target.files);
        }
        // Reset input value to allow re-uploading the same file
        event.target.value = null;
    };
    
    const handleFolderChangeEvent = (event) => {
        if (event.target.files.length > 0) {
            if (window.confirm(`This will upload ${event.target.files.length} files to the cloud. Continue?`)) {
                handleUpload(event.target.files);
            }
        }
         // Reset input value to allow re-uploading the same folder
        event.target.value = null;
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
    
    const handleDownload = async (fileToDownload = selectedFile) => {
        if (!fileToDownload) return;
        try {
            toast.info(`Downloading ${fileToDownload.name}...`);
            await api.downloadFile(fileToDownload.name);
        } catch (error) {
            toast.error(`Failed to download ${fileToDownload.name}.`);
        }
    };
    
    const handleSyncDownload = async () => {
        setIsSyncModalOpen(false);
        if (window.confirm(`This will download all ${allFiles.length} remote files to your default Downloads folder. Continue?`)) {
            toast.info("Starting sync download...");
            for (const file of allFiles) {
                await new Promise(resolve => setTimeout(resolve, 300));
                await handleDownload(file);
            }
            toast.success("Sync download process finished.");
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

    const handleDragEvents = (e, isOver) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDraggingOver(isOver);
    };

    const handleDrop = (e) => {
        handleDragEvents(e, false);
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleUpload(e.dataTransfer.files);
            e.dataTransfer.clearData();
        }
    };
    
    return (
        <div 
            className={`main-window ${isDraggingOver ? 'drag-over' : ''}`} 
            onDragEnter={(e) => handleDragEvents(e, true)}
            onDragLeave={(e) => handleDragEvents(e, false)}
            onDragOver={(e) => handleDragEvents(e, true)}
            onDrop={handleDrop}
        >
            <input type="file" multiple ref={fileInputRef} style={{ display: 'none' }} onChange={handleFileChangeEvent} />
            <input type="file" webkitdirectory="" directory="" multiple ref={folderInputRef} style={{ display: 'none' }} onChange={handleFolderChangeEvent} />

            <ToastContainer position="bottom-right" theme="dark" />
            <div className="header">
              <div className="header-left">
                <h3>Cloud Drive</h3>
                <span>Logged in as: <strong>{user.username}</strong></span>
              </div>
              <button className="btn-icon logout-btn" onClick={logout}>
                <LogoutIcon /> Logout
              </button>
            </div>
            <TopBar
                onUploadClick={() => fileInputRef.current.click()}
                onDelete={handleDelete}
                onDownload={() => handleDownload()}
                onRefresh={refreshFiles}
                onSyncClick={() => setIsSyncModalOpen(true)}
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
                onDownload={() => handleDownload()}
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
            {isSyncModalOpen && (
                <SyncPromptModal
                    onClose={() => setIsSyncModalOpen(false)}
                    onUploadClick={() => {
                        setIsSyncModalOpen(false);
                        folderInputRef.current.click();
                    }}
                    onDownloadClick={handleSyncDownload}
                />
            )}
        </div>
    );
}

