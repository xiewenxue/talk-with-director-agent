import { Box, Button, TextField, Typography, Avatar, Paper, Dialog, DialogContent } from '@mui/material';
import { Send, Image as ImageIcon } from '@mui/icons-material';
import { ConfigData, Message, MessageSetter } from '../App';
import { useRef, useEffect, useState } from 'react';

type MessagePanelProps = {
  config: ConfigData;
  messages: Message[];
  setMessages: MessageSetter;
};

export default function MessagePanel({ config, messages, setMessages }: MessagePanelProps) {
  const [inputText, setInputText] = useState('');
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const buildAssistantMessage = (content: string): Message => ({
    id: (Date.now() + 1).toString(),
    role: 'assistant',
    content,
    timestamp: Date.now(),
  });

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleImageSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null;
    if (!file) return;
    setSelectedImage(URL.createObjectURL(file));
  };

  const handleSend = async () => {
    if (!inputText.trim() && !selectedImage) return;
    
    let userMessage: Message;
    let fileToSend: File | null = null;
    const messageToSend = inputText.trim(); // 保存要发送的消息内容

    if (selectedImage) {
      // 如果有选中的图片，需要获取原始文件
      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      const file = fileInput?.files?.[0] || null;
      if (file) {
        fileToSend = file;
        userMessage = {
          id: Date.now().toString(),
          role: 'user',
          content: messageToSend || `[上传图片: ${file.name}]`,
          timestamp: Date.now(),
          image: selectedImage,
        };
      } else {
        userMessage = {
          id: Date.now().toString(),
          role: 'user',
          content: messageToSend,
          timestamp: Date.now(),
        };
      }
    } else {
      userMessage = {
        id: Date.now().toString(),
        role: 'user',
        content: messageToSend,
        timestamp: Date.now(),
      };
    }
    
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInputText('');
    setSelectedImage(null);
    setIsTyping(true);
    
    // 清空文件输入
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    if (fileInput) fileInput.value = '';

    try {
      // 如果有图片，发送到图片分析接口
      if (fileToSend) {
        const formData = new FormData();
        formData.append('file', fileToSend);
        if (messageToSend) {
          formData.append('question', messageToSend);
        }

        const res = await fetch('/api/upload-image', {
          method: 'POST',
          body: formData,
        });
        const data = await res.json();
        
        setMessages((prev) => [
          ...prev,
          buildAssistantMessage(
            data.status === 'ok'
              ? data.response
              : `图片上传失败: ${data.detail || data.message || '未知错误'}`,
          ),
        ]);
      } else {
        // 普通文字消息
        const res = await fetch('/api/message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: messageToSend }),
        });
        const data = await res.json();
        
        setMessages((prev) => [
          ...prev,
          buildAssistantMessage(data.status === 'ok' ? data.response : `错误: ${data.detail || '未知错误'}`),
        ]);
      }
    } catch (error) {
      setMessages((prev) => [...prev, buildAssistantMessage('网络错误，请稍后重试')]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '600px' }}>
      {/* 消息列表区域 */}
      <Box 
        sx={{ 
          flex: 1, 
          overflowY: 'auto', 
          p: 2, 
          bgcolor: '#f5f5f5',
          borderRadius: 2,
          mb: 2
        }}
      >
        {messages.length === 0 && (
          <Box sx={{ textAlign: 'center', color: '#999', mt: 10 }}>
            <Typography variant="body1">开始与李安导演对话吧...</Typography>
          </Box>
        )}
        
        {messages.map((msg) => (
          <Box
            key={msg.id}
            sx={{
              display: 'flex',
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
              mb: 2,
            }}
          >
            {msg.role === 'assistant' && (
              <Avatar sx={{ mr: 1, bgcolor: '#95ec69' }}>李</Avatar>
            )}
            
            <Paper
              sx={{
                p: 2,
                maxWidth: '70%',
                bgcolor: msg.role === 'user' ? '#95ec69' : '#ffffff',
                borderRadius: 2,
                boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
              }}
            >
              {msg.image && (
                <Box sx={{ mb: 1 }}>
                  <img
                    src={msg.image}
                    alt="上传的图片"
                    onClick={() => setPreviewImage(msg.image ?? null)}
                    style={{
                      maxWidth: '200px',
                      maxHeight: '200px',
                      borderRadius: 4,
                      objectFit: 'contain',
                      cursor: 'zoom-in',
                    }}
                  />
                </Box>
              )}
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                {msg.content}
              </Typography>
            </Paper>
            
            {msg.role === 'user' && (
              <Avatar sx={{ ml: 1, bgcolor: '#1296db' }}>我</Avatar>
            )}
          </Box>
        ))}
        
        {/* AI正在输入提示 */}
        {isTyping && (
          <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 2 }}>
            <Avatar sx={{ mr: 1, bgcolor: '#95ec69' }}>李</Avatar>
            <Paper
              sx={{
                p: 2,
                bgcolor: '#ffffff',
                borderRadius: 2,
                boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
                display: 'flex',
                alignItems: 'center',
                gap: 1,
              }}
            >
              <Typography variant="body2" sx={{ color: '#999' }}>正在输入...</Typography>
            </Paper>
          </Box>
        )}
        
        <div ref={messagesEndRef} />
      </Box>

      <Dialog open={Boolean(previewImage)} onClose={() => setPreviewImage(null)} maxWidth="lg">
        <DialogContent sx={{ p: 1 }}>
          {previewImage && (
            <img
              src={previewImage}
              alt="图片预览"
              style={{ maxWidth: '90vw', maxHeight: '85vh', display: 'block' }}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* 输入区域 */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {/* 图片预览区域 */}
        {selectedImage && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 1, bgcolor: '#f5f5f5', borderRadius: 2 }}>
            <img 
              src={selectedImage} 
              alt="预览" 
              style={{ width: '60px', height: '60px', objectFit: 'cover', borderRadius: 4 }}
            />
            <Typography variant="caption" sx={{ flex: 1 }}>已选择图片</Typography>
            <Button 
              size="small" 
              onClick={() => {
                setSelectedImage(null);
                const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
                if (fileInput) fileInput.value = '';
              }}
            >
              取消
            </Button>
          </Box>
        )}
        
        {/* 输入框和按钮 */}
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
          <Button
            component="label"
            variant="outlined"
            disabled={!config.configured}
            sx={{ minWidth: 48, height: 56 }}
          >
            <ImageIcon />
            <input hidden accept="image/*" type="file" onChange={handleImageSelect} />
          </Button>
          
          <TextField
            fullWidth
            multiline
            maxRows={4}
            placeholder={config.configured ? '输入消息...' : '请先配置 API Key'}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={!config.configured}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
              },
            }}
          />
          
          <Button
            variant="contained"
            disabled={!config.configured || (!inputText.trim() && !selectedImage)}
            onClick={handleSend}
            sx={{ minWidth: 48, height: 56, bgcolor: '#07c160', '&:hover': { bgcolor: '#06ad56' } }}
          >
            <Send />
          </Button>
        </Box>

        <Typography variant="caption" sx={{ color: '#64748b', pl: 0.5 }}>
          仅作交流学习，不代表导演本人立场
        </Typography>
      </Box>
    </Box>
  );
}
