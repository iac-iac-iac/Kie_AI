import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../../components/ui/Button";
import { ConfirmDialog } from "../../../components/ui/ConfirmDialog";
import { Input } from "../../../components/ui/Input";
import type { ChatFolder, ChatSummary } from "../../../lib/api";
import { cn } from "../../../lib/utils";

interface ChatSidebarProps {
  folders: ChatFolder[];
  chats: ChatSummary[];
  activeChatId: string | null;
  selectedFolderId: string | null;
  searchQuery: string;
  collapsedFolders: Set<string>;
  canCreateChat: boolean;
  creatingChat: boolean;
  onSearchChange: (value: string) => void;
  onSelectFolder: (folderId: string | null) => void;
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void;
  onNewFolder: () => void;
  onDeleteChat: (chatId: string) => void;
  onMoveChat: (chatId: string, folderId: string | null) => void;
  onRenameChat: (chatId: string, title: string) => void;
  onRenameFolder: (folderId: string, name: string) => void;
  onDeleteFolder: (folderId: string) => void;
  onToggleFolderCollapse: (folderId: string) => void;
}

export function ChatSidebar({
  folders,
  chats,
  activeChatId,
  selectedFolderId,
  searchQuery,
  collapsedFolders,
  canCreateChat,
  creatingChat,
  onSearchChange,
  onSelectFolder,
  onSelectChat,
  onNewChat,
  onNewFolder,
  onDeleteChat,
  onMoveChat,
  onRenameChat,
  onRenameFolder,
  onDeleteFolder,
  onToggleFolderCollapse,
}: ChatSidebarProps) {
  const { t } = useTranslation();
  const [dragChatId, setDragChatId] = useState<string | null>(null);
  const [deleteFolderId, setDeleteFolderId] = useState<string | null>(null);

  const isSearching = searchQuery.trim().length > 0;
  const unfiledChats = chats.filter((c) => !c.folder_id);

  return (
    <aside className="glass-panel flex w-64 shrink-0 flex-col rounded-2xl border border-[var(--glass-border)]">
      <div className="flex flex-col gap-2 border-b border-[var(--glass-border)] p-3">
        <div className="flex gap-2">
          <Button
            type="button"
            className="flex-1"
            disabled={!canCreateChat}
            onClick={onNewChat}
          >
            {creatingChat ? "…" : t("chats.newChat")}
          </Button>
          <Button type="button" variant="outline" onClick={onNewFolder} title={t("chats.newFolder")}>
            +
          </Button>
        </div>
        <Input
          type="search"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder={t("chats.search")}
          aria-label={t("chats.search")}
        />
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {isSearching ? (
          chats.length === 0 ? (
            <p className="px-3 py-2 text-sm text-muted">{t("chats.emptyState")}</p>
          ) : (
            chats.map((chat) => (
              <ChatItem
                key={chat.id}
                chat={chat}
                active={chat.id === activeChatId}
                onSelect={() => onSelectChat(chat.id)}
                onDelete={() => onDeleteChat(chat.id)}
                onRename={(title) => onRenameChat(chat.id, title)}
                onDragStart={() => setDragChatId(chat.id)}
                onDragEnd={() => setDragChatId(null)}
              />
            ))
          )
        ) : (
          <>
            <button
              type="button"
              className={cn(
                "mb-1 w-full rounded-lg px-3 py-2 text-left text-sm transition-colors",
                selectedFolderId === null ? "bg-accent text-white" : "nav-link-inactive",
              )}
              onClick={() => onSelectFolder(null)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => {
                if (dragChatId) onMoveChat(dragChatId, null);
                setDragChatId(null);
              }}
            >
              {t("chats.allChats")}
            </button>

            {folders.map((folder) => {
              const folderChats = chats.filter((c) => c.folder_id === folder.id);
              const collapsed = collapsedFolders.has(folder.id);

              return (
                <div key={folder.id} className="mb-2">
                  <div
                    className={cn(
                      "group flex items-center gap-1 rounded-lg px-1 py-1 transition-colors",
                      selectedFolderId === folder.id
                        ? "bg-[var(--hover-bg)]"
                        : "hover:bg-[var(--hover-bg)]",
                    )}
                  >
                    <button
                      type="button"
                      className="shrink-0 rounded px-1 text-xs text-muted hover:text-primary"
                      onClick={() => onToggleFolderCollapse(folder.id)}
                      title={collapsed ? t("chats.expandFolder") : t("chats.collapseFolder")}
                      aria-expanded={!collapsed}
                    >
                      {collapsed ? "▸" : "▾"}
                    </button>
                    <button
                      type="button"
                      className={cn(
                        "min-w-0 flex-1 truncate px-1 py-1 text-left text-sm font-medium",
                        selectedFolderId === folder.id ? "text-primary" : "text-muted",
                      )}
                      onClick={() => onSelectFolder(folder.id)}
                      onDragOver={(e) => e.preventDefault()}
                      onDrop={() => {
                        if (dragChatId) onMoveChat(dragChatId, folder.id);
                        setDragChatId(null);
                      }}
                    >
                      📁 {folder.name}
                    </button>
                    <button
                      type="button"
                      className="shrink-0 rounded px-1 text-xs text-muted opacity-0 transition-opacity group-hover:opacity-100 hover:text-primary"
                      onClick={() => {
                        const name = window.prompt(t("chats.folderRename"), folder.name);
                        if (name?.trim()) onRenameFolder(folder.id, name.trim());
                      }}
                      title={t("chats.folderRename")}
                    >
                      ✎
                    </button>
                    <button
                      type="button"
                      className="shrink-0 rounded px-1 text-xs text-muted opacity-0 transition-opacity group-hover:opacity-100 hover:text-status-error"
                      onClick={() => setDeleteFolderId(folder.id)}
                      title={t("chats.folderDelete")}
                    >
                      ×
                    </button>
                  </div>
                  {!collapsed &&
                    (selectedFolderId === folder.id || selectedFolderId === null) &&
                    folderChats.map((chat) => (
                      <ChatItem
                        key={chat.id}
                        chat={chat}
                        active={chat.id === activeChatId}
                        onSelect={() => onSelectChat(chat.id)}
                        onDelete={() => onDeleteChat(chat.id)}
                        onRename={(title) => onRenameChat(chat.id, title)}
                        onDragStart={() => setDragChatId(chat.id)}
                        onDragEnd={() => setDragChatId(null)}
                      />
                    ))}
                </div>
              );
            })}

            {selectedFolderId === null &&
              unfiledChats.map((chat) => (
                <ChatItem
                  key={chat.id}
                  chat={chat}
                  active={chat.id === activeChatId}
                  onSelect={() => onSelectChat(chat.id)}
                  onDelete={() => onDeleteChat(chat.id)}
                  onRename={(title) => onRenameChat(chat.id, title)}
                  onDragStart={() => setDragChatId(chat.id)}
                  onDragEnd={() => setDragChatId(null)}
                />
              ))}
          </>
        )}
      </div>

      <ConfirmDialog
        open={deleteFolderId !== null}
        title={t("chats.folderDelete")}
        message={t("chats.folderDeleteConfirm")}
        confirmLabel={t("chats.folderDelete")}
        cancelLabel={t("common.cancel")}
        destructive
        onConfirm={() => {
          if (deleteFolderId) onDeleteFolder(deleteFolderId);
          setDeleteFolderId(null);
        }}
        onCancel={() => setDeleteFolderId(null)}
      />
    </aside>
  );
}

function ChatItem({
  chat,
  active,
  onSelect,
  onDelete,
  onRename,
  onDragStart,
  onDragEnd,
}: {
  chat: ChatSummary;
  active: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onRename: (title: string) => void;
  onDragStart: () => void;
  onDragEnd: () => void;
}) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(chat.title);

  const commitRename = () => {
    const trimmed = draft.trim();
    setEditing(false);
    if (trimmed && trimmed !== chat.title) onRename(trimmed);
    else setDraft(chat.title);
  };

  return (
    <div
      draggable={!editing}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      className={cn(
        "group mt-1 flex items-center gap-1 rounded-lg px-3 py-2 text-sm transition-colors",
        active ? "bg-accent text-white" : "nav-link-inactive",
      )}
    >
      {editing ? (
        <input
          className="min-w-0 flex-1 rounded bg-black/20 px-1 py-0.5 text-sm outline-none"
          value={draft}
          autoFocus
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commitRename}
          onKeyDown={(e) => {
            if (e.key === "Enter") commitRename();
            if (e.key === "Escape") {
              setDraft(chat.title);
              setEditing(false);
            }
          }}
          onClick={(e) => e.stopPropagation()}
        />
      ) : (
        <button
          type="button"
          className="min-w-0 flex-1 truncate text-left"
          onClick={onSelect}
          onDoubleClick={(e) => {
            e.preventDefault();
            setDraft(chat.title);
            setEditing(true);
          }}
        >
          {chat.title}
        </button>
      )}
      <button
        type="button"
        className={cn(
          "shrink-0 rounded px-1 text-xs opacity-0 transition-opacity group-hover:opacity-100",
          active ? "text-white/80 hover:text-white" : "text-muted hover:text-primary",
        )}
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        title={t("chats.deleteChat")}
      >
        ×
      </button>
    </div>
  );
}
