'use client'
import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './ui/sidebar';
import Head from 'next/head';
import { GoSidebarCollapse, GoSidebarExpand } from 'react-icons/go';

type Message = {
  id: number,
  text: string,
  sender: 'user' | 'bot'
};

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const messageContainerRef = useRef<HTMLDivElement>(null);

  const handleSend = async () => {
    if (input.trim() !== '') {
      const userMessage: Message = {
        id: messages.length + 1,
        text: input,
        sender: 'user'
      };
      // use functional form to make sure we work with most recent state even in async scenarios
      setMessages((prevMessages) => [...prevMessages, userMessage]);
      setInput('');

      // send query to chat endpoint
      try {
        const response = await fetch('http://127.0.0.1:5000/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ query: input }),
        });

        if (response.ok) {
          const data = await response.json();
          const botMessage: Message = {
            id: messages.length + 2,
            text: data.answer,
            sender: 'bot'
          };
          setMessages((prevMessages) => [...prevMessages, botMessage]);
        } else {
          console.error('Error: failed to fetch bot response');
        }
      } catch (error) {
        console.error('Error:', error);
      }

      // Simulating bot response
      // setTimeout(() => {
      //   const botMessage: Message = {
      //     id: messages.length + 2,
      //     text: 'This is a bot response',
      //     sender: 'bot'
      //   };
      //   setMessages((prevMessages) => [...prevMessages, botMessage]);
      // }, 1000);
    }
  };

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setInput(event.target.value);
  }

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter') {
      handleSend();
    }
  };

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  const scrollToBottom = () => {
    messageContainerRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  return (
    <main>
      <Head>
        <meta property="og:image" content="/thumbnail.svg" />
        <meta property="og:image:type" content="image/svg+xml" />
      </Head>
      <div className="flex h-screen">
        <Sidebar isOpen={isSidebarOpen} toggleSidebar={toggleSidebar} />
        <div className="flex flex-col flex-1 h-full max-w-full mx-auto border border-gray-300 rounded-lg overflow-hidden">
          <button
            onClick={toggleSidebar}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 m-4 self-start"
          >
            {isSidebarOpen ? <GoSidebarExpand /> : <GoSidebarCollapse />}
          </button>
          <div className="flex-1 p-4 overflow-y-auto bg-gray-100">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`p-3 my-2 rounded-lg ${
                  message.sender === 'user' ? 'bg-green-200 self-end' : 'bg-white self-start'
                }`}
              >
                {message.text}
              </div>
            ))}
            <div ref={messageContainerRef} />
          </div>
          <div className="flex p-4 bg-white border-t border-gray-300">
            <input
              type="text"
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Type a message..."
              className="flex-1 p-2 border border-gray-300 rounded-lg mr-4"
            />
            <button
              onClick={handleSend}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </main>
  );
};

export default Chat;