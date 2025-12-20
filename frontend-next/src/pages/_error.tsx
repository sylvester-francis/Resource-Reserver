import React from 'react';

function Error({ statusCode }: { statusCode?: number }) {
    return (
        <div style={{
            display: 'flex',
            minHeight: '100vh',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: '#f9fafb'
        }}>
            <div style={{ textAlign: 'center' }}>
                <h1 style={{ fontSize: '3.75rem', fontWeight: 'bold', color: '#111827' }}>
                    {statusCode || 'Error'}
                </h1>
                <p style={{ marginTop: '1rem', fontSize: '1.25rem', color: '#4b5563' }}>
                    {statusCode === 404
                        ? 'Page not found'
                        : 'An error occurred'}
                </p>
                <a
                    href="/"
                    style={{
                        display: 'inline-block',
                        marginTop: '1.5rem',
                        padding: '0.75rem 1.5rem',
                        backgroundColor: '#2563eb',
                        color: 'white',
                        borderRadius: '0.5rem',
                        textDecoration: 'none'
                    }}
                >
                    Go Home
                </a>
            </div>
        </div>
    );
}

Error.getInitialProps = ({ res, err }: { res?: { statusCode?: number }; err?: { statusCode?: number } }) => {
    const statusCode = res ? res.statusCode : err ? err.statusCode : 404;
    return { statusCode };
};

export default Error;
