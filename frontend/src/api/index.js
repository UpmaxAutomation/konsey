/**
 * API Module Index - Barrel export for all API functions.
 *
 * This file re-exports everything from the modular API files,
 * maintaining backward compatibility with existing imports.
 */

// Re-export client utilities
export {
  API_BASE,
  handleResponse,
  safeFetch,
  getAuthHeaders,
  refreshAccessToken,
  authFetch,
} from './client.js';

// Re-export all conversation functions
export {
  listConversations,
  createConversation,
  getConversation,
  deleteConversation,
  sendMessage,
  sendMessageStream,
  sendQuickMessageStream,
  moveConversationToFolder,
  updateConversationTags,
  uploadFile,
  listFiles,
  deleteFile,
  importConversation,
  forkConversation,
  cancelStream,
} from './conversations.js';

// Re-export all config functions
export {
  getApiKeys,
  setApiKey,
  deleteApiKey,
  getConfig,
  updateConfig,
  resetConfig,
  getPresets,
  applyPreset,
  estimateCost,
  getUsage,
  resetUsage,
  refreshModels,
  getPersonas,
  setPersona,
  createCustomPersona,
  getFeatures,
  setFeatures,
  getBudget,
  setBudget,
  getBudgetAlerts,
  resetBudget,
  clearBudgetAlerts,
  getCacheStats,
  clearCache,
  routeQuery,
  getQuickRoute,
  getCouncilRoute,
  listAPIKeys,
  createAPIKey,
  updateAPIKey,
  revokeAPIKey,
} from './config.js';

// Re-export all tools functions
export {
  executeCode,
  getMemoryContext,
  getMemoryStats,
  clearMemory,
  rememberFact,
  setPreference,
  searchConversations,
  getSearchSuggestions,
} from './tools.js';

// Re-export all images functions
export {
  generateImage,
  getImageProviders,
  listImages,
  getImage,
  deleteImage,
} from './images.js';

// Re-export all voice functions
export {
  textToSpeech,
  transcribeAudio,
  getTTSProviders,
  getSTTProviders,
  listTTSHistory,
  listTranscriptions,
} from './voice.js';

// Re-export all agents functions
export {
  createAgent,
  listAgents,
  getAgent,
  runAgent,
  runAgentStream,
  cancelAgent,
  deleteAgent,
} from './agents.js';

// Re-export all integrations functions
export {
  getIntegrationStatus,
  gdriveListFiles,
  gdriveGetFile,
  gdriveUploadFile,
  slackSendMessage,
  slackSendWebhook,
  slackListChannels,
  githubListRepos,
  githubGetFile,
  githubListIssues,
  githubCreateIssue,
  githubListPRs,
} from './integrations.js';

// Re-export all analytics functions
export {
  getAnalyticsOverview,
  getModelAnalytics,
  getConversationAnalytics,
  exportAnalytics,
} from './analytics.js';

// Re-export all templates functions
export {
  listTemplates,
  getTemplateCategories,
  getTemplate,
  createTemplate,
  updateTemplate,
  deleteTemplate,
  fillTemplate,
} from './templates.js';

// Re-export all projects functions
export {
  listProjects,
  createProject,
  getProject,
  updateProject,
  deleteProject,
  addKnowledgeToProject,
  removeKnowledgeFromProject,
  getKnowledgeContent,
  createConversationInProject,
  moveConversationToProject,
  getProjectMemory,
  getProjectMemoryStats,
  clearProjectMemory,
  addProjectFact,
  setProjectPreference,
  listFolders,
  createFolder,
  deleteFolder,
  listAllTags,
  listTeams,
  createTeam,
  getTeam,
  updateTeam,
  deleteTeam,
  inviteTeamMember,
  removeTeamMember,
  shareConversationToTeam,
  listTeamConversations,
} from './projects.js';

// Re-export all RAG functions
export {
  embedDocument,
  embedAllDocuments,
  semanticSearch,
  getRAGStatus,
  deleteDocumentEmbeddings,
} from './rag.js';

// Re-export all layers functions
export {
  createLayer,
  listLayers,
  getLayer,
  updateLayer,
  deleteLayer,
  assignDocuments,
  reorderLayers,
} from './layers.js';

// Re-export all ratings functions
export {
  submitRating,
  getRating,
  getModelRatings,
  getRatingRecommendations,
  getRatingAnalytics,
  clearRatings,
} from './ratings.js';

// Re-export all batch functions
export {
  createBatchJob,
  listBatchJobs,
  getBatchJob,
  deleteBatchJob,
} from './batch.js';

// Re-export all export functions
export {
  exportConversation,
  exportMarkdown,
  exportJSON,
  exportHTML,
  shareConversation,
  getSharedConversation,
} from './export.js';

// Re-export all mentions functions
export {
  getBacklinks,
  getMentionGraph,
} from './mentions.js';

// Re-export all snapshots functions
export {
  listSnapshots,
  createSnapshot,
  getSnapshot,
  restoreSnapshot,
  deleteSnapshot,
} from './snapshots.js';

// Re-export all boards functions
export {
  listBoards,
  createBoard,
  getBoard,
  updateBoard,
  updateBoardViewport,
  deleteBoard,
  listCards,
  createCard,
  updateCard,
  batchUpdateCardPositions,
  deleteCard,
  listEdges,
  createEdge,
  deleteEdge,
  createCardFromMessage,
  createCardsFromCouncilTurn,
  runCouncilFromBoard,
  runCardAIAction,
  runBoardAIAction,
  getBoardMemory,
  boardMemoryAction,
  deleteBoardFact,
} from './boards.js';

// Build the api object for backward compatibility
// This maintains the `api.methodName()` usage pattern
import * as conversations from './conversations.js';
import * as config from './config.js';
import * as tools from './tools.js';
import * as images from './images.js';
import * as voice from './voice.js';
import * as agents from './agents.js';
import * as integrations from './integrations.js';
import * as analytics from './analytics.js';
import * as templates from './templates.js';
import * as projects from './projects.js';
import * as ratings from './ratings.js';
import * as batch from './batch.js';
import * as exportModule from './export.js';
import * as boards from './boards.js';
import * as rag from './rag.js';
import * as layers from './layers.js';
import * as mentions from './mentions.js';
import * as snapshots from './snapshots.js';

export const api = {
  // Conversations
  listConversations: conversations.listConversations,
  createConversation: conversations.createConversation,
  getConversation: conversations.getConversation,
  deleteConversation: conversations.deleteConversation,
  sendMessage: conversations.sendMessage,
  sendMessageStream: conversations.sendMessageStream,
  sendQuickMessageStream: conversations.sendQuickMessageStream,
  moveConversationToFolder: conversations.moveConversationToFolder,
  updateConversationTags: conversations.updateConversationTags,
  uploadFile: conversations.uploadFile,
  listFiles: conversations.listFiles,
  deleteFile: conversations.deleteFile,
  importConversation: conversations.importConversation,
  forkConversation: conversations.forkConversation,
  cancelStream: conversations.cancelStream,

  // Config
  getApiKeys: config.getApiKeys,
  setApiKey: config.setApiKey,
  deleteApiKey: config.deleteApiKey,
  getConfig: config.getConfig,
  updateConfig: config.updateConfig,
  resetConfig: config.resetConfig,
  getPresets: config.getPresets,
  applyPreset: config.applyPreset,
  estimateCost: config.estimateCost,
  getUsage: config.getUsage,
  resetUsage: config.resetUsage,
  refreshModels: config.refreshModels,
  getPersonas: config.getPersonas,
  setPersona: config.setPersona,
  createCustomPersona: config.createCustomPersona,
  getFeatures: config.getFeatures,
  setFeatures: config.setFeatures,
  getBudget: config.getBudget,
  setBudget: config.setBudget,
  getBudgetAlerts: config.getBudgetAlerts,
  resetBudget: config.resetBudget,
  clearBudgetAlerts: config.clearBudgetAlerts,
  getCacheStats: config.getCacheStats,
  clearCache: config.clearCache,
  routeQuery: config.routeQuery,
  getQuickRoute: config.getQuickRoute,
  getCouncilRoute: config.getCouncilRoute,
  listAPIKeys: config.listAPIKeys,
  createAPIKey: config.createAPIKey,
  updateAPIKey: config.updateAPIKey,
  revokeAPIKey: config.revokeAPIKey,

  // Tools
  executeCode: tools.executeCode,
  getMemoryContext: tools.getMemoryContext,
  getMemoryStats: tools.getMemoryStats,
  clearMemory: tools.clearMemory,
  rememberFact: tools.rememberFact,
  setPreference: tools.setPreference,
  searchConversations: tools.searchConversations,
  getSearchSuggestions: tools.getSearchSuggestions,

  // Images
  generateImage: images.generateImage,
  getImageProviders: images.getImageProviders,
  listImages: images.listImages,
  getImage: images.getImage,
  deleteImage: images.deleteImage,

  // Voice
  textToSpeech: voice.textToSpeech,
  transcribeAudio: voice.transcribeAudio,
  getTTSProviders: voice.getTTSProviders,
  getSTTProviders: voice.getSTTProviders,
  listTTSHistory: voice.listTTSHistory,
  listTranscriptions: voice.listTranscriptions,

  // Agents
  createAgent: agents.createAgent,
  listAgents: agents.listAgents,
  getAgent: agents.getAgent,
  runAgent: agents.runAgent,
  runAgentStream: agents.runAgentStream,
  cancelAgent: agents.cancelAgent,
  deleteAgent: agents.deleteAgent,

  // Integrations
  getIntegrationStatus: integrations.getIntegrationStatus,
  gdriveListFiles: integrations.gdriveListFiles,
  gdriveGetFile: integrations.gdriveGetFile,
  gdriveUploadFile: integrations.gdriveUploadFile,
  slackSendMessage: integrations.slackSendMessage,
  slackSendWebhook: integrations.slackSendWebhook,
  slackListChannels: integrations.slackListChannels,
  githubListRepos: integrations.githubListRepos,
  githubGetFile: integrations.githubGetFile,
  githubListIssues: integrations.githubListIssues,
  githubCreateIssue: integrations.githubCreateIssue,
  githubListPRs: integrations.githubListPRs,

  // Analytics
  getAnalyticsOverview: analytics.getAnalyticsOverview,
  getModelAnalytics: analytics.getModelAnalytics,
  getConversationAnalytics: analytics.getConversationAnalytics,
  exportAnalytics: analytics.exportAnalytics,

  // Templates
  listTemplates: templates.listTemplates,
  getTemplateCategories: templates.getTemplateCategories,
  getTemplate: templates.getTemplate,
  createTemplate: templates.createTemplate,
  updateTemplate: templates.updateTemplate,
  deleteTemplate: templates.deleteTemplate,
  fillTemplate: templates.fillTemplate,

  // Projects
  listProjects: projects.listProjects,
  createProject: projects.createProject,
  getProject: projects.getProject,
  updateProject: projects.updateProject,
  deleteProject: projects.deleteProject,
  addKnowledgeToProject: projects.addKnowledgeToProject,
  removeKnowledgeFromProject: projects.removeKnowledgeFromProject,
  getKnowledgeContent: projects.getKnowledgeContent,
  createConversationInProject: projects.createConversationInProject,
  moveConversationToProject: projects.moveConversationToProject,
  getProjectMemory: projects.getProjectMemory,
  getProjectMemoryStats: projects.getProjectMemoryStats,
  clearProjectMemory: projects.clearProjectMemory,
  addProjectFact: projects.addProjectFact,
  setProjectPreference: projects.setProjectPreference,
  listFolders: projects.listFolders,
  createFolder: projects.createFolder,
  deleteFolder: projects.deleteFolder,
  listAllTags: projects.listAllTags,
  listTeams: projects.listTeams,
  createTeam: projects.createTeam,
  getTeam: projects.getTeam,
  updateTeam: projects.updateTeam,
  deleteTeam: projects.deleteTeam,
  inviteTeamMember: projects.inviteTeamMember,
  removeTeamMember: projects.removeTeamMember,
  shareConversationToTeam: projects.shareConversationToTeam,
  listTeamConversations: projects.listTeamConversations,

  // Ratings
  submitRating: ratings.submitRating,
  getRating: ratings.getRating,
  getModelRatings: ratings.getModelRatings,
  getRatingRecommendations: ratings.getRatingRecommendations,
  getRatingAnalytics: ratings.getRatingAnalytics,
  clearRatings: ratings.clearRatings,

  // Batch
  createBatchJob: batch.createBatchJob,
  listBatchJobs: batch.listBatchJobs,
  getBatchJob: batch.getBatchJob,
  deleteBatchJob: batch.deleteBatchJob,

  // Export
  exportConversation: exportModule.exportConversation,
  exportMarkdown: exportModule.exportMarkdown,
  exportJSON: exportModule.exportJSON,
  exportHTML: exportModule.exportHTML,
  shareConversation: exportModule.shareConversation,
  getSharedConversation: exportModule.getSharedConversation,

  // Boards
  listBoards: boards.listBoards,
  createBoard: boards.createBoard,
  getBoard: boards.getBoard,
  updateBoard: boards.updateBoard,
  updateBoardViewport: boards.updateBoardViewport,
  deleteBoard: boards.deleteBoard,
  listCards: boards.listCards,
  createCard: boards.createCard,
  updateCard: boards.updateCard,
  batchUpdateCardPositions: boards.batchUpdateCardPositions,
  deleteCard: boards.deleteCard,
  listEdges: boards.listEdges,
  createEdge: boards.createEdge,
  deleteEdge: boards.deleteEdge,
  createCardFromMessage: boards.createCardFromMessage,
  createCardsFromCouncilTurn: boards.createCardsFromCouncilTurn,
  runCouncilFromBoard: boards.runCouncilFromBoard,
  runCardAIAction: boards.runCardAIAction,
  runBoardAIAction: boards.runBoardAIAction,
  getBoardMemory: boards.getBoardMemory,
  boardMemoryAction: boards.boardMemoryAction,
  deleteBoardFact: boards.deleteBoardFact,

  // RAG
  embedDocument: rag.embedDocument,
  embedAllDocuments: rag.embedAllDocuments,
  semanticSearch: rag.semanticSearch,
  getRAGStatus: rag.getRAGStatus,
  deleteDocumentEmbeddings: rag.deleteDocumentEmbeddings,

  // Layers
  createLayer: layers.createLayer,
  listLayers: layers.listLayers,
  getLayer: layers.getLayer,
  updateLayer: layers.updateLayer,
  deleteLayer: layers.deleteLayer,
  assignDocuments: layers.assignDocuments,
  reorderLayers: layers.reorderLayers,

  // Mentions
  getBacklinks: mentions.getBacklinks,
  getMentionGraph: mentions.getMentionGraph,

  // Snapshots
  listSnapshots: snapshots.listSnapshots,
  createSnapshot: snapshots.createSnapshot,
  getSnapshot: snapshots.getSnapshot,
  restoreSnapshot: snapshots.restoreSnapshot,
  deleteSnapshot: snapshots.deleteSnapshot,
};
