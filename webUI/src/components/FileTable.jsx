import React, { useState, useMemo } from 'react';
import { formatDate, formatSize } from '../utils/formatters';
import ContextMenu from './ContextMenu';

export default function FileTable({ files, loading, selectedFile, onFileSelect, onFileDoubleClick, onRename, onDelete, onDownload }) {
    const [sortConfig, setSortConfig] = useState({ key: 'name', direction: 'ascending' });
    const [contextMenu, setContextMenu] = useState(null);

    const sortedFiles = useMemo(() => {
        let sortableFiles = [...files];
        if (sortConfig.key) {
            sortableFiles.sort((a, b) => {
                if (a[sortConfig.key] < b[sortConfig.key]) {
                    return sortConfig.direction === 'ascending' ? -1 : 1;
                }
                if (a[sortConfig.key] > b[sortConfig.key]) {
                    return sortConfig.direction === 'ascending' ? 1 : -1;
                }
                return 0;
            });
        }
        return sortableFiles;
    }, [files, sortConfig]);

    const requestSort = (key) => {
        let direction = 'ascending';
        if (sortConfig.key === key && sortConfig.direction === 'ascending') {
            direction = 'descending';
        }
        setSortConfig({ key, direction });
    };

    const getSortIndicator = (key) => {
        if (sortConfig.key !== key) return '↕';
        return sortConfig.direction === 'ascending' ? '↑' : '↓';
    };

    const handleRightClick = (event, file) => {
        event.preventDefault();
        onFileSelect(file);
        setContextMenu({ x: event.pageX, y: event.pageY, file });
    };

    const handleCloseContextMenu = () => setContextMenu(null);

    const menuItems = [
        { label: 'Rename', action: onRename },
        { label: 'Download', action: onDownload },
        { label: 'Delete', action: onDelete },
    ];

    const columns = [
        { key: 'name', label: 'Name' },
        { key: 'size', label: 'Size', format: formatSize, align: 'right' },
        { key: 'uploaded_by', label: 'Uploaded By' },
        { key: 'last_modified_by', label: 'Modified By' },
        { key: 'created_at', label: 'Date Created', format: formatDate },
        { key: 'modified_at', label: 'Date Modified', format: formatDate },
    ];

    return (
        <div className="table-container">
            <table>
                <thead>
                    <tr>
                        {columns.map(col => (
                           <th key={col.key} onClick={() => requestSort(col.key)} style={{ textAlign: col.align || 'left' }}>
                               {col.label} {getSortIndicator(col.key)}
                           </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {loading ? (
                        <tr><td colSpan={columns.length} style={{textAlign: 'center'}}>Loading files...</td></tr>
                    ) : sortedFiles.length === 0 ? (
                         <tr><td colSpan={columns.length} style={{textAlign: 'center'}}>No files found.</td></tr>
                    ) : (
                        sortedFiles.map(file => (
                            <tr
                                key={file.name}
                                className={selectedFile?.name === file.name ? 'selected' : ''}
                                onClick={() => onFileSelect(file)}
                                onDoubleClick={() => onFileDoubleClick(file)}
                                onContextMenu={(e) => handleRightClick(e, file)}
                            >
                                {columns.map(col => (
                                    <td key={col.key} style={{ textAlign: col.align || 'left' }}>
                                        {col.format ? col.format(file[col.key]) : file[col.key]}
                                    </td>
                                ))}
                            </tr>
                        ))
                    )}
                </tbody>
            </table>
            {contextMenu && (
                <ContextMenu
                    x={contextMenu.x}
                    y={contextMenu.y}
                    items={menuItems}
                    onClose={handleCloseContextMenu}
                />
            )}
        </div>
    );
}