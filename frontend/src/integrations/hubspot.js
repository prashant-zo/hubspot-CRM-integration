// hubspot.js

import { useState, useEffect } from "react";
import {
    Box,
    Button,
    CircularProgress
} from '@mui/material';
import axios from 'axios';


export const HubSpotIntegration = ({ user, org, integrationParams, setIntegrationParams}) => {
    const [isConnected, setIsConnected] = useState(false);
    const [isConnecting, setIsConnecting] = useState(false);

    const handleConnectClick = async () => {
        try {
            setIsConnecting(true);
            const formData = new FormData();
            formData.append('user_id', user);
            formData.append('org_id', org);
            // Update the endpoint to HubSpot
            const response = await axios.post(`http://localhost:8000/integrations/hubspot/authorize`, formData);
            const authURL = response?.data;

            const newWindow = window.open(authURL, 'HubSpot Authorization', 'width=600,height=600,resizable,scrollbars'); // Added resizable,scrollbars

            // Polling for the window to close
            const pollTimer = window.setInterval(async () => { 
                if (newWindow?.closed) { 
                    window.clearInterval(pollTimer);
                    
                    await handleWindowClosed();
                }
            }, 500); 
        } catch (e) {
            setIsConnecting(false);
            alert(e?.response?.data?.detail || 'Failed to start HubSpot authorization.');
            console.error("HubSpot Auth Start Error:", e);
        }
    };

    // Function to handle logic when the OAuth window closes
    const handleWindowClosed = async () => {
        try {
            const formData = new FormData();
            formData.append('user_id', user);
            formData.append('org_id', org);
            // Update the endpoint to HubSpot
            const response = await axios.post(`http://localhost:8000/integrations/hubspot/credentials`, formData);
            const credentials = response.data;
            if (credentials) {
                setIsConnected(true);
                // Update the type to 'HubSpot'
                setIntegrationParams(prev => ({ ...prev, credentials: credentials, type: 'HubSpot' }));
            }
        } catch (e) {
            alert(e?.response?.data?.detail || 'Failed to fetch HubSpot credentials.');
            console.error("HubSpot Credentials Fetch Error:", e);
        } finally {
            setIsConnecting(false);
        }
    };

    useEffect(() => {
        if (integrationParams?.type === 'HubSpot' && integrationParams?.credentials) {
            setIsConnected(true);
        } else {
            setIsConnected(false);
        }
    }, [integrationParams]);

    return (
        <>
        <Box sx={{mt: 2}}>
            Parameters
            <Box display='flex' alignItems='center' justifyContent='center' sx={{mt: 2}}>
                <Button
                    variant='contained'
                    onClick={handleConnectClick} 
                    color={isConnected ? 'success' : 'primary'}
                    disabled={isConnecting || isConnected} // Disable if connecting OR already connected
                    style={{ // Original style from airtable.js
                        pointerEvents: isConnected ? 'none' : 'auto',
                        cursor: isConnected ? 'default' : 'pointer',
                        opacity: isConnected ? 1 : undefined
                    }}
                >
                    {isConnected ? 'HubSpot Connected' : isConnecting ? <CircularProgress size={24} color="inherit" /> : 'Connect to HubSpot'}
                </Button>
            </Box>
        </Box>
      </>
    );
}
