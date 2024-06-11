import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

type MessageProps = {
  text: string,
  sender: 'user' | 'bot';
};

const Message: React.FC<MessageProps> = ({ text, sender }) => {
  return (
    <div
      className={`p-3 my-2 rounded-lg ${
        sender === 'user' ? 'bg-green-200 self-end' : 'bg-white self-start'
      }`}
    >
      {sender === 'bot' ? (
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
      ) : (
        text
      )}
    </div>
  );
};

export default Message;