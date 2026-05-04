/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_GH_USER?: string
  readonly VITE_GH_REPO?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
