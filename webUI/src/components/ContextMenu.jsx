import React, { useEffect, useRef } from 'react';

export default function ContextMenu({ x, y, items, onClose }) {
    const menuRef = useRef(null);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (menuRef.current && !menuRef.current.contains(event.target)) {
                onClose();
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [onClose]);

    const handleItemClick = (item) => {
        if (!item.disabled) {
            item.action();
            // CRITICAL FIX: Always close the menu after an action.
            // This ensures it is re-rendered with fresh state next time it opens.
            onClose();
        }
    };

    return (
        <div ref={menuRef} className="context-menu" style={{ top: y, left: x }}>
            <ul>
                {items.map(item => (
                    <li 
                        key={item.label} 
                        className={`${item.type === 'checkbox' ? 'checkbox-item' : ''} ${item.disabled ? 'disabled' : ''}`}
                        onClick={() => handleItemClick(item)}
                    >
                        {item.type === 'checkbox' && (
                            <input type="checkbox" checked={item.checked} readOnly disabled={item.disabled} />
                        )}
                        <span>{item.label}</span>
                    </li>
                ))}
            </ul>
        </div>
    );
}

