// WebSocket connection
const roomId = { room,id };
const chatSocket = new WebSocket(
    'ws://' + window.location.host + '/ws/chat/' + roomId + '/'
);

chatSocket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    // Handle message types: message, typing, user_joined, etc.
};

chatSocket.onclose = function(e) {
    console.error('Chat socket closed');
};

// Send message
function sendMessage(message) {
    chatSocket.send(JSON.stringify({
        'type': 'message',
        'message': message
    }));
}

// Typing indicator
function sendTyping(isTyping) {
    chatSocket.send(JSON.stringify({
        'type': 'typing',
        'is_typing': isTyping
    }));
}