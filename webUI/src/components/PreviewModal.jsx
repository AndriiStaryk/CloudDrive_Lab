import React, { useState, useEffect } from 'react';
import * as api from '../api/apiClient.js';
import { toast } from 'react-toastify';

export default function PreviewModal({ file, onClose, onSave }) {
    const [content, setContent] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    const [isEditing, setIsEditing] = useState(false);
    const [error, setError] = useState('');

    const isImage = file.name.toLowerCase().match(/\.(jpg|jpeg|png)$/);
    const isText = file.name.toLowerCase().match(/\.(c|py|txt)$/);

    useEffect(() => {
        const fetchContent = async () => {
            setIsLoading(true);
            try {
                const response = await api.getFileContent(file.name);
                if (response.data.encoding === 'base64') {
                    setContent(`data:image/png;base64,${response.data.content}`);
                } else {
                    setContent(response.data.content);
                }
            } catch (err) {
                setError('Could not load file content.');
            } finally {
                setIsLoading(false);
            }
        };
        fetchContent();
    }, [file.name]);

    const handleSave = async () => {
        try {
            await api.updateFileContent(file.name, content);
            toast.success("File saved successfully!");
            setIsEditing(false);
            onSave(); // Refresh the file list to show updated modified date/user
        } catch (err) {
            toast.error("Failed to save file.");
        }
    };
    
    return (
        <div className="modal-backdrop" onClick={onClose}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>{file.name}</h2>
                    <button onClick={onClose} className="close-btn">&times;</button>
                </div>
                <div className="modal-body">
                    {isLoading && <p>Loading preview...</p>}
                    {error && <p className="error-text">{error}</p>}
                    {!isLoading && !error && (
                        isImage ? (
                            <img src={content} alt={file.name} style={{ maxWidth: '100%', maxHeight: '70vh' }} />
                        ) : isText ? (
                            <textarea
                                value={content}
                                readOnly={!isEditing}
                                onChange={(e) => setContent(e.target.value)}
                            />
                        ) : <p>Preview not available.</p>
                    )}
                </div>
                <div className="modal-footer">
                     {isText && !isEditing && (
                        <button className="btn-secondary" onClick={() => setIsEditing(true)}>Edit</button>
                    )}
                    {isText && isEditing && (
                        <button className="btn-primary" onClick={handleSave}>Save</button>
                    )}
                    <button className="btn-secondary" onClick={onClose}>Close</button>
                </div>
            </div>
        </div>
    );
}