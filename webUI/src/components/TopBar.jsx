import React from 'react';
import { UploadIcon, DownloadIcon, DeleteIcon, RefreshIcon, SyncIcon } from '../assets/icons.jsx';

export default function TopBar({ 
    onUploadClick, 
    onDelete, 
    onDownload, 
    onRefresh, 
    onSyncClick, 
    selectedFile, 
    activeFilter, 
    onFilterChange 
}) {
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
                <button className="btn-icon" onClick={onUploadClick}><UploadIcon /> Upload File</button>
                <button className="btn-icon" onClick={onDownload} disabled={!selectedFile}><DownloadIcon /> Download</button>
                <button className="btn-icon" onClick={onDelete} disabled={!selectedFile}><DeleteIcon /> Delete</button>
                <button className="btn-icon" onClick={onSyncClick}><SyncIcon /> Sync Folder</button>
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

