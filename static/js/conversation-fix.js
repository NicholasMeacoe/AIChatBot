// Direct fix for conversation creation issue
document.addEventListener('DOMContentLoaded', function() {
    console.log("Conversation fix script loaded");
    
    // Global variable to track if we're initializing
    window.isInitializingConversation = false;
    
    // Function to get existing conversations
    async function getExistingConversations() {
        try {
            const response = await fetch('/api/conversations');
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error("Error fetching conversations:", error);
            return [];
        }
    }
    
    // Function to create a new conversation
    async function createNewConversation() {
        if (window.isInitializingConversation) {
            console.log("Already initializing conversation, skipping");
            return null;
        }
        
        window.isInitializingConversation = true;
        
        try {
            const response = await fetch('/api/conversations', { method: 'POST' });
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }
            const data = await response.json();
            console.log("Created new conversation:", data.id);
            window.currentConversationId = data.id;
            return data.id;
        } catch (error) {
            console.error("Error creating conversation:", error);
            return null;
        } finally {
            window.isInitializingConversation = false;
        }
    }
    
    // Function to initialize conversation
    async function initializeConversation() {
        // First check if we already have a conversation ID
        if (window.currentConversationId) {
            console.log("Already have conversation ID:", window.currentConversationId);
            return window.currentConversationId;
        }
        
        // Check for existing conversations
        const conversations = await getExistingConversations();
        if (conversations && conversations.length > 0) {
            // Use the first existing conversation
            window.currentConversationId = conversations[0].id;
            console.log("Using existing conversation:", window.currentConversationId);
            return window.currentConversationId;
        }
        
        // Create a new conversation if none exist
        return await createNewConversation();
    }
    
    // Replace the original loadConversations function
    if (typeof window.loadConversations === 'function') {
        const originalLoadConversations = window.loadConversations;
        
        window.loadConversations = async function() {
            try {
                const result = await originalLoadConversations.apply(this, arguments);
                
                // After loading conversations, ensure we have a current conversation ID
                if (!window.currentConversationId) {
                    await initializeConversation();
                }
                
                return result;
            } catch (error) {
                console.error("Error in patched loadConversations:", error);
                // Still try to initialize conversation
                await initializeConversation();
                throw error;
            }
        };
        
        console.log("Patched loadConversations function");
    }
    
    // Replace the original createNewChat function
    if (typeof window.createNewChat === 'function') {
        const originalCreateNewChat = window.createNewChat;
        
        window.createNewChat = async function() {
            if (window.isInitializingConversation) {
                console.log("Already initializing conversation, skipping createNewChat");
                return;
            }
            
            window.isInitializingConversation = true;
            
            try {
                return await originalCreateNewChat.apply(this, arguments);
            } catch (error) {
                console.error("Error in patched createNewChat:", error);
                throw error;
            } finally {
                window.isInitializingConversation = false;
            }
        };
        
        console.log("Patched createNewChat function");
    }
    
    // Initialize conversation on page load
    setTimeout(async function() {
        await initializeConversation();
    }, 1000);
    
    console.log("Conversation fix applied");
});
