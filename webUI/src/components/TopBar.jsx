import React, { useRef } from 'react';
import { UploadIcon, DownloadIcon, DeleteIcon, RefreshIcon } from '../assets/icons.jsx';

export default function TopBar({ onUpload, onDelete, onDownload, onRefresh, selectedFile, activeFilter, onFilterChange }) {
    const fileInputRef = useRef(null);

    const handleUploadClick = () => {
        fileInputRef.current.click();
    };
    
    const handleFileChange = (event) => {
        if (event.target.files.length > 0) {
            onUpload(event.target.files);
        }
    };

    const FilterButton = ({ filterType, label }) => (
        <button
            className={`btn-filter ${activeFilter === filterType ? 'active' : ''}`}
            onClick={() => onFilterChange(filterType)}
        >
            {label}
        </button>
    );

    return (
        <div className="top-bar">
            <div className="action-buttons">
                <input type="file" multiple ref={fileInputRef} style={{ display: 'none' }} onChange={handleFileChange} />
                <button className="btn-icon" onClick={handleUploadClick}><UploadIcon /> Upload</button>
                <button className="btn-icon" onClick={onDownload} disabled={!selectedFile}><DownloadIcon /> Download</button>
                <button className="btn-icon" onClick={onDelete} disabled={!selectedFile}><DeleteIcon /> Delete</button>
            </div>
            <div className="filter-buttons">
                <span>Filter by:</span>
                <FilterButton filterType="all" label="All Files" />
                <FilterButton filterType="py" label="Python (.py)" />
                <FilterButton filterType="img" label="Images" />
            </div>
            <div className="refresh-button">
                 <button className="btn-icon" onClick={onRefresh}><RefreshIcon /> Refresh</button>
            </div>
        </div>
    );
}