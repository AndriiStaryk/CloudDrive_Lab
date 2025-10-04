import React from 'react';
import { UploadIcon, DownloadIcon } from '../assets/icons.jsx';

export default function SyncPromptModal({ onClose, onUploadClick, onDownloadClick }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content sync-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Sync Folder</h2>
          <button onClick={onClose} className="close-btn">&times;</button>
        </div>
        <div className="modal-body">
          <p>Choose a synchronization action.</p>
          <div className="modal-options">
            <button className="btn-icon" onClick={onUploadClick}>
              <UploadIcon /> Upload from Local Folder to Cloud
            </button>
            <button className="btn-icon" onClick={onDownloadClick}>
              <DownloadIcon /> Download from Cloud to Local Folder
            </button>
          </div>
          <p className="modal-note">
            Note: When downloading, all remote files will be saved to your browser's default "Downloads" folder due to web security policies.
          </p>
        </div>
      </div>
    </div>
  );
}
