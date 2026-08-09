import React from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import { useAppSelector } from '../hooks/redux'

interface PrivateRouteProps {
  children?: React.ReactNode
  requiredRoles?: string[]
}

const PrivateRoute: React.FC<PrivateRouteProps> = ({ children, requiredRoles }) => {
  const { isAuthenticated, user } = useAppSelector((state) => state.auth)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (requiredRoles && user && !requiredRoles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />
  }

  return children ? <>{children}</> : <Outlet />
}

export default PrivateRoute