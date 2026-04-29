import React from 'react'

interface AlertBannerProps {
  type: 'success' | 'error'
  text: string
  onClose: () => void
  classNamePrefix?: string
}

export const AlertBanner: React.FC<AlertBannerProps> = ({ type, text, onClose, classNamePrefix = 'networking' }) => {
  return (
    <div className={`${classNamePrefix}-alertbox ${classNamePrefix}-alertbox--${type}`} role="alert">
      <div className={`${classNamePrefix}-alertbox-body`}>
        <span className={`${classNamePrefix}-alertbox-icon`}>{type === 'success' ? '✓' : '!'}</span>
        <span>{text}</span>
      </div>
      <button
        className={`${classNamePrefix}-alertbox-close`}
        onClick={onClose}
        aria-label="Close notification"
      >
        &times;
      </button>
    </div>
  )
}
