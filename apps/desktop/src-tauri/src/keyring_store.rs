const SERVICE: &str = "kie-ai-desktop";
const USER: &str = "api-key";

pub fn set_api_key(key: &str) -> Result<(), String> {
    let entry = keyring::Entry::new(SERVICE, USER).map_err(|e| e.to_string())?;
    entry.set_password(key).map_err(|e| e.to_string())
}

pub fn get_api_key() -> Result<Option<String>, String> {
    let entry = keyring::Entry::new(SERVICE, USER).map_err(|e| e.to_string())?;
    match entry.get_password() {
        Ok(key) => Ok(Some(key)),
        Err(keyring::Error::NoEntry) => Ok(None),
        Err(e) => Err(e.to_string()),
    }
}

pub fn delete_api_key() -> Result<(), String> {
    let entry = keyring::Entry::new(SERVICE, USER).map_err(|e| e.to_string())?;
    match entry.delete_credential() {
        Ok(()) => Ok(()),
        Err(keyring::Error::NoEntry) => Ok(()),
        Err(e) => Err(e.to_string()),
    }
}
