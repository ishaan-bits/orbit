class KnowledgeBaseError(Exception):
    """Base class for knowledge base domain errors."""


class UnsupportedFileTypeError(KnowledgeBaseError):
    def __init__(self, filename: str) -> None:
        super().__init__(f"File type of '{filename}' is not supported")
        self.filename = filename


class FileTooLargeError(KnowledgeBaseError):
    def __init__(self, limit_bytes: int) -> None:
        super().__init__(
            f"File exceeds the {limit_bytes // (1024 * 1024)}MB size limit"
        )
        self.limit_bytes = limit_bytes


class EmptyFileError(KnowledgeBaseError):
    def __init__(self) -> None:
        super().__init__("Uploaded file is empty")


class FolderNotFoundError(KnowledgeBaseError):
    def __init__(self, folder_id: str) -> None:
        super().__init__(f"Folder '{folder_id}' was not found")
        self.folder_id = folder_id


class FolderAlreadyExistsError(KnowledgeBaseError):
    def __init__(self, name: str) -> None:
        super().__init__(f"A folder named '{name}' already exists")
        self.name = name


class DocumentNotFoundError(KnowledgeBaseError):
    def __init__(self, document_id: str) -> None:
        super().__init__(f"Document '{document_id}' was not found")
        self.document_id = document_id


class ConversationNotFoundError(KnowledgeBaseError):
    def __init__(self, conversation_id: str) -> None:
        super().__init__(f"Conversation '{conversation_id}' was not found")
        self.conversation_id = conversation_id


class EmailAlreadyRegisteredError(KnowledgeBaseError):
    def __init__(self, email: str) -> None:
        super().__init__(f"An account with email '{email}' already exists")
        self.email = email


class InvalidRoleError(KnowledgeBaseError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidCredentialsError(KnowledgeBaseError):
    def __init__(self) -> None:
        super().__init__("Invalid email or password")


class FolderAccessDeniedError(KnowledgeBaseError):
    def __init__(self, folder_name: str) -> None:
        super().__init__(
            f"Your role does not have access to the folder '{folder_name}'"
        )
        self.folder_name = folder_name
