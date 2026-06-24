import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { api, ApiError, type ChatSummary } from "../../lib/api";
import { mapApiError } from "../../lib/apiErrors";
import { exportChatToFile } from "../../lib/exportChat";
import { formatModelLabel } from "../../lib/modelCapabilities";
import { showToast } from "../../lib/toast";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { apiLockMessageKey, useApiReady } from "../../hooks/useHasApiKey";
import { useHotkeys } from "../../hooks/useHotkeys";
import { ChatComposer } from "./components/ChatComposer";
import { ChatSidebar } from "./components/ChatSidebar";
import { ChatThread } from "./components/ChatThread";
import { ModelSelector } from "./components/ModelSelector";
import { useChatStream } from "./hooks/useChatStream";
import { useChats, useMessages } from "./hooks/useChats";

export function ChatsPage() {
  const { t } = useTranslation();
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [newChatModelId, setNewChatModelId] = useState<string>("");
  const [toolsEnabled, setToolsEnabled] = useState(false);
  const [chatSearch, setChatSearch] = useState("");
  const [messageSearch, setMessageSearch] = useState("");
  const [collapsedFolders, setCollapsedFolders] = useState<Set<string>>(new Set());
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const [exporting, setExporting] = useState(false);
  const { isReady: hasApiKey, lockReason } = useApiReady();
  const [createError, setCreateError] = useState<string | null>(null);

  const debouncedChatSearch = useDebouncedValue(chatSearch, 300);
  const debouncedMessageSearch = useDebouncedValue(messageSearch, 300);

  const {
    models,
    folders,
    chats,
    isLoading,
    sidecarError,
    refetchModels,
    createChat,
    deleteChat,
    moveChat,
    renameChat,
    createFolder,
    renameFolder,
    deleteFolder,
  } = useChats(debouncedChatSearch, selectedFolderId);

  const messagesQuery = useMessages(activeChatId, debouncedMessageSearch);
  const [activeChatMeta, setActiveChatMeta] = useState<ChatSummary | null>(null);

  useEffect(() => {
    if (!activeChatId) {
      setActiveChatMeta(null);
      return;
    }
    const found = chats.find((c) => c.id === activeChatId);
    if (found) setActiveChatMeta(found);
  }, [chats, activeChatId]);

  const activeChat =
    chats.find((c) => c.id === activeChatId) ??
    (activeChatMeta?.id === activeChatId ? activeChatMeta : null);

  const {
    streamingText,
    thinking,
    streaming,
    error,
    sendAndStream,
    stop,
    clearError,
  } = useChatStream(activeChatId);

  useEffect(() => {
    if (models.length > 0 && !newChatModelId) {
      setNewChatModelId(models[0].id);
    }
  }, [models, newChatModelId]);

  useEffect(() => {
    if (activeChat) setTitleDraft(activeChat.title);
  }, [activeChat?.id, activeChat?.title]);

  const canCreateChat = models.length > 0 && !createChat.isPending && hasApiKey;

  const handleNewChat = async () => {
    setCreateError(null);
    const modelId = newChatModelId || models[0]?.id;
    if (!modelId) {
      setCreateError(t("chats.errorNoModels"));
      return;
    }
    try {
      const chat = await createChat.mutateAsync(modelId);
      setActiveChatId(chat.id);
      setSelectedFolderId(chat.folder_id);
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        showToast(t("errors.rateLimit"));
      }
      setCreateError(mapApiError(err, t));
    }
  };

  useHotkeys([
    {
      key: "n",
      ctrl: true,
      handler: () => {
        if (canCreateChat) void handleNewChat();
      },
    },
  ]);

  const handleDeleteChat = async (chatId: string) => {
    await deleteChat.mutateAsync(chatId);
    if (activeChatId === chatId) setActiveChatId(null);
  };

  const handleRenameChat = (chatId: string, title: string) => {
    void renameChat.mutateAsync({ chatId, title });
  };

  const handleRenameFolder = (folderId: string, name: string) => {
    void renameFolder.mutateAsync({ folderId, name });
  };

  const handleDeleteFolder = (folderId: string) => {
    void deleteFolder.mutateAsync(folderId);
    if (selectedFolderId === folderId) setSelectedFolderId(null);
  };

  const toggleFolderCollapse = (folderId: string) => {
    setCollapsedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(folderId)) next.delete(folderId);
      else next.add(folderId);
      return next;
    });
  };

  const commitTitleRename = () => {
    setEditingTitle(false);
    if (!activeChat) return;
    const trimmed = titleDraft.trim();
    if (trimmed && trimmed !== activeChat.title) {
      handleRenameChat(activeChat.id, trimmed);
    } else {
      setTitleDraft(activeChat.title);
    }
  };

  const handleExport = async () => {
    if (!activeChat) return;
    setExporting(true);
    try {
      const saved = await exportChatToFile(activeChat.id, activeChat.title);
      if (saved) showToast(t("chats.exportSuccess"));
    } catch {
      showToast(t("chats.exportFailed"));
    } finally {
      setExporting(false);
    }
  };

  const activeModel = models.find((m) => m.id === (activeChat?.model_id ?? newChatModelId));

  if (isLoading) {
    return (
      <Card className="mx-auto max-w-2xl text-center">
        <p className="text-muted">{t("chats.loading")}</p>
      </Card>
    );
  }

  return (
    <div className="flex h-full min-h-0 gap-4">
      <ChatSidebar
        folders={folders}
        chats={chats}
        activeChatId={activeChatId}
        selectedFolderId={selectedFolderId}
        searchQuery={chatSearch}
        collapsedFolders={collapsedFolders}
        canCreateChat={canCreateChat}
        creatingChat={createChat.isPending}
        onSearchChange={setChatSearch}
        onSelectFolder={setSelectedFolderId}
        onSelectChat={setActiveChatId}
        onNewChat={() => void handleNewChat()}
        onNewFolder={() => void createFolder.mutate()}
        onDeleteChat={(id) => void handleDeleteChat(id)}
        onMoveChat={(chatId, folderId) =>
          void moveChat.mutate({ chatId, folderId })
        }
        onRenameChat={handleRenameChat}
        onRenameFolder={handleRenameFolder}
        onDeleteFolder={handleDeleteFolder}
        onToggleFolderCollapse={toggleFolderCollapse}
      />

      <div className="glass-panel flex min-w-0 flex-1 flex-col rounded-2xl border border-[var(--glass-border)]">
        {(sidecarError || createError) && (
          <div className="border-b border-[var(--glass-border)] bg-red-500/10 px-4 py-3 text-sm text-status-error">
            <p>{sidecarError ?? createError}</p>
            {sidecarError && (
              <Button
                type="button"
                variant="outline"
                className="mt-2"
                onClick={() => void refetchModels()}
              >
                {t("chats.retry")}
              </Button>
            )}
          </div>
        )}

        {!activeChat ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-6 p-8">
            <div className="text-center">
              <h2 className="text-accent text-xl font-semibold">{t("chats.welcomeTitle")}</h2>
              <p className="mt-2 text-sm text-muted">{t("chats.welcomeHint")}</p>
            </div>
            {models.length > 0 && (
              <ModelSelector
                models={models}
                value={newChatModelId}
                onChange={setNewChatModelId}
                disabled={!hasApiKey}
              />
            )}
            {!hasApiKey && (
              <p className="max-w-md text-center text-sm text-muted">
                {t(apiLockMessageKey(lockReason))}{" "}
                <Link to="/settings" className="text-accent underline-offset-2 hover:underline">
                  {t("apiKey.goToSettings")}
                </Link>
              </p>
            )}
            <Button
              type="button"
              disabled={!canCreateChat}
              onClick={() => void handleNewChat()}
            >
              {createChat.isPending ? t("chats.creating") : t("chats.newChat")}
            </Button>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-3 border-b border-[var(--glass-border)] px-4 py-3">
              {editingTitle ? (
                <input
                  className="input-field min-w-0 flex-1 text-sm"
                  value={titleDraft}
                  autoFocus
                  onChange={(e) => setTitleDraft(e.target.value)}
                  onBlur={commitTitleRename}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") commitTitleRename();
                    if (e.key === "Escape") {
                      setTitleDraft(activeChat.title);
                      setEditingTitle(false);
                    }
                  }}
                />
              ) : (
                <button
                  type="button"
                  className="min-w-0 flex-1 truncate text-left text-sm font-medium text-primary hover:underline"
                  onClick={() => {
                    setTitleDraft(activeChat.title);
                    setEditingTitle(true);
                  }}
                  title={t("chats.rename")}
                >
                  {activeChat.title}
                </button>
              )}
              <div className="flex shrink-0 items-center gap-2">
                {activeModel && (
                  <span className="text-xs text-subtle">
                    {formatModelLabel(activeModel.id, activeModel.display_name, t)}
                  </span>
                )}
                <Button
                  type="button"
                  variant="outline"
                  className="text-xs"
                  disabled={exporting}
                  onClick={() => void handleExport()}
                >
                  {exporting ? "…" : t("chats.export")}
                </Button>
              </div>
            </div>

            <ChatThread
              messages={messagesQuery.data ?? []}
              streamingText={streamingText}
              thinking={thinking}
              messageSearch={messageSearch}
              onMessageSearchChange={setMessageSearch}
            />

            {error && (
              <div className="mx-4 mb-2 rounded-lg bg-red-500/10 px-3 py-2 text-sm text-status-error">
                {error}
                <button
                  type="button"
                  className="ml-2 underline"
                  onClick={clearError}
                >
                  {t("chats.dismiss")}
                </button>
              </div>
            )}

            <div className="border-t border-[var(--glass-border)] p-4">
              <ChatComposer
                disabled={!hasApiKey}
                streaming={streaming}
                model={activeModel}
                toolsEnabled={toolsEnabled}
                onToolsEnabledChange={setToolsEnabled}
                onSend={(content) => void sendAndStream(content, toolsEnabled)}
                onStop={stop}
                onAttachImage={
                  activeModel?.supports_vision
                    ? (file) => api.uploadChatImage(file)
                    : undefined
                }
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
