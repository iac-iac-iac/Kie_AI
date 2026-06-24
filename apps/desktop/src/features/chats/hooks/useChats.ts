import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../../lib/api";

export function useChats(searchQuery: string, selectedFolderId: string | null) {
  const queryClient = useQueryClient();
  const { t } = useTranslation();

  const modelsQuery = useQuery({
    queryKey: ["chat-models"],
    queryFn: () => api.listChatModels(),
    retry: 2,
  });

  const foldersQuery = useQuery({
    queryKey: ["chat-folders"],
    queryFn: () => api.listFolders(),
  });

  const chatsQuery = useQuery({
    queryKey: ["chats", searchQuery],
    queryFn: () =>
      api.listChats({
        q: searchQuery || undefined,
      }),
  });

  const createChat = useMutation({
    mutationFn: (modelId: string) =>
      api.createChat(modelId, selectedFolderId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["chats"] });
    },
  });

  const deleteChat = useMutation({
    mutationFn: (chatId: string) => api.deleteChat(chatId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["chats"] });
    },
  });

  const moveChat = useMutation({
    mutationFn: ({ chatId, folderId }: { chatId: string; folderId: string | null }) =>
      api.updateChat(chatId, { folder_id: folderId }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["chats"] });
    },
  });

  const renameChat = useMutation({
    mutationFn: ({ chatId, title }: { chatId: string; title: string }) =>
      api.updateChat(chatId, { title }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["chats"] });
    },
  });

  const createFolder = useMutation({
    mutationFn: () => {
      const name = window.prompt(t("chats.folderNamePrompt"));
      if (!name?.trim()) throw new Error("cancelled");
      return api.createFolder(name.trim());
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["chat-folders"] });
    },
  });

  const renameFolder = useMutation({
    mutationFn: ({ folderId, name }: { folderId: string; name: string }) =>
      api.updateFolder(folderId, name),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["chat-folders"] });
    },
  });

  const deleteFolder = useMutation({
    mutationFn: (folderId: string) => api.deleteFolder(folderId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["chat-folders"] });
      void queryClient.invalidateQueries({ queryKey: ["chats"] });
    },
  });

  const sidecarError =
    modelsQuery.isError
      ? t("chats.errorSidecar")
      : modelsQuery.isSuccess && modelsQuery.data.length === 0
        ? t("chats.errorNoModels")
        : null;

  return {
    models: modelsQuery.data ?? [],
    folders: foldersQuery.data ?? [],
    chats: chatsQuery.data ?? [],
    isLoading: modelsQuery.isLoading || chatsQuery.isLoading,
    sidecarError,
    refetchModels: () => void modelsQuery.refetch(),
    createChat,
    deleteChat,
    moveChat,
    renameChat,
    createFolder,
    renameFolder,
    deleteFolder,
  };
}

export function useMessages(chatId: string | null, messageSearch = "") {
  return useQuery({
    queryKey: ["messages", chatId, messageSearch],
    queryFn: () => api.getMessages(chatId!, messageSearch || undefined),
    enabled: !!chatId,
  });
}
