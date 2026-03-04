import { createContext, useContext, useState } from 'react'

const UserContext = createContext(null)

export function UserProvider({ children }) {
  const [username, setUsernameState] = useState(
    () => localStorage.getItem('gapsight_username') || ''
  )

  const setUsername = (name) => {
    localStorage.setItem('gapsight_username', name)
    setUsernameState(name)
  }

  return (
    <UserContext.Provider value={{ username, setUsername }}>
      {children}
    </UserContext.Provider>
  )
}

export function useUser() {
  return useContext(UserContext)
}
