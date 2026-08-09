import React from 'react'
import { Tabs, Tab, Box } from '@mui/material'
import { useLocation, useNavigate } from 'react-router-dom'

import UsersPage from './UsersPage'
import RoleManagement from './RoleManagement'

function useTabQuery(defaultTab: string) {
    const location = useLocation()
    const navigate = useNavigate()
    const params = new URLSearchParams(location.search)
    const current = params.get('tab') || defaultTab
    const setTab = (tab: string) => {
        const next = new URLSearchParams(location.search)
        next.set('tab', tab)
        navigate({ pathname: location.pathname, search: next.toString() }, { replace: true })
    }
    return { current, setTab }
}

const IdentityHubPage: React.FC = () => {
    const { current, setTab } = useTabQuery('users')
    const tabIndex = ['users', 'roles'].indexOf(current)

    return (
        <Box sx={{ width: '100%' }}>
            <Tabs
                value={tabIndex === -1 ? 0 : tabIndex}
                onChange={(_, idx) => setTab(['users', 'roles'][idx])}
                sx={{ mb: 2 }}
            >
                <Tab label="Users" />
                <Tab label="Roles & Permissions" />
            </Tabs>

            <Box role="tabpanel" hidden={current !== 'users'}>
                {current === 'users' && <UsersPage />}
            </Box>
            <Box role="tabpanel" hidden={current !== 'roles'}>
                {current === 'roles' && <RoleManagement />}
            </Box>
        </Box>
    )
}

export default IdentityHubPage


