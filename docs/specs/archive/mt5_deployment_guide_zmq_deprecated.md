# MT5 Server Deployment & Implementation Guide

This document outlines the steps to deploy the MQL5 Execution Server (`ZmqServer.mq5`) for the Unified OMS Bridge.

## 1. Prerequisites

### 1.1 MetaTrader 5 Terminal
Ensure MT5 is installed and updated to the latest build (requires Build > 3000 for Python integration features, though we use ZMQ).

### 1.2 Dependencies
The bridge relies on **ZeroMQ** for communication and **JAson** for JSON parsing.

1.  **ZeroMQ Library (`libzmq.dll`)**:
    *   Download `libzmq.dll` (usually v4.3.x) compiled for x64.
    *   Place in: `%APPDATA%\MetaQuotes\Terminal\<ID>\MQL5\Libraries\`
    *   *Note: Ensure you have the corresponding `Zmq.mqh` wrapper.*

2.  **JSON Library (`JAson.mqh`)**:
    *   Download `JAson.mqh` (standard MQL5 JSON parser).
    *   Place in: `%APPDATA%\MetaQuotes\Terminal\<ID>\MQL5\Include\`

3.  **ZMQ Wrapper (`Zmq.mqh`)**:
    *   Place the ZeroMQ MQL wrapper in: `%APPDATA%\MetaQuotes\Terminal\<ID>\MQL5\Include\`

## 2. Server Implementation (`ZmqServer.mq5`)

Create or update `MQL5/Experts/ZmqServer.mq5` with the following code. This implementation matches the `mt5_oms_design.md` protocol.

```cpp
//+------------------------------------------------------------------+
//|                                                    ZmqServer.mq5 |
//|                                    Copyright 2026, Quant Platform|
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, Quant Platform"
#property link      "https://www.mql5.com"
#property version   "1.00"

//--- Imports
#include <Zmq.mqh>
#include <JAson.mqh>
#include <Trade\Trade.mqh>

//--- Input Parameters
input int InpRepPort = 5555;   // REQ/REP Port (Commands)
input int InpPullPort = 5556;  // PULL Port (Data Stream - logic inverted for server PUSH)
input int InpPushPort = 5557;  // PUSH Port (Status)

//--- Globals
Context context("mt5_context");
Socket socket_rep(context, ZMQ_REP);
Socket socket_push(context, ZMQ_PUSH); // Used to push Ticks/Events to Python
CTrade trade;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   //--- Initialize ZMQ
   Print("Initializing ZMQ Server...");
   
   if(!socket_rep.bind(StringFormat("tcp://*:%d", InpRepPort))) {
      Print("Failed to bind REP socket on port ", InpRepPort);
      return(INIT_FAILED);
   }
   
   if(!socket_push.connect(StringFormat("tcp://localhost:%d", InpPullPort))) {
       // Note: Python binds PULL, so MT5 connects PUSH to it.
       // Check client.py: client connects PULL to 5556? 
       // WAIT: The design says MT5 PUSH -> Python PULL. 
       // Usually Python binds PULL? No, usually ZMQ Server (MT5) binds, Client connects.
       // Let's check topology: 
       // Python (Client) REQ -> Connects to MT5 REP (Bound)
       // MT5 (Server) PUSH -> Connects to Python PULL (Bound) OR Binds PUSH?
       // Let's assume standard DWX: MT5 Binds everything. Python Connects.
       // Re-reading client.py: 
       // client.py: socket_pull.connect(...5556)
       // So Python Connects. Therefore MT5 must BIND 5556.
      Print("Binding PUSH socket on port ", InpPullPort);
      if (!socket_push.bind(StringFormat("tcp://*:%d", InpPullPort))) {
          Print("Failed to bind PUSH socket");
          return(INIT_FAILED);
      }
   }
   
   // Enable Timer for polling
   EventSetMillisecondTimer(10); // 10ms poll interval
   
   Print("ZMQ Server Initialized. Listening on REP:", InpRepPort, " PUSH:", InpPullPort);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   // Context logic handles cleanup usually, but explicit close is good
   // socket_rep.close();
   // socket_push.close();
   Print("ZMQ Server Stopped");
  }

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
  {
   // Stream Tick Data
   CJAVal data;
   MqlTick tick;
   
   if(SymbolInfoTick(_Symbol, tick)) {
      data["type"] = "DATA";
      data["symbol"] = _Symbol;
      data["bid"] = tick.bid;
      data["ask"] = tick.ask;
      data["time"] = (long)tick.time;
      
      // Send non-blocking
      string msg = data.Serialize();
      socket_push.send(msg, true); // true = non-blocking (ZMQ_DONTWAIT)
   }
  }

//+------------------------------------------------------------------+
//| Timer function                                                   |
//+------------------------------------------------------------------+
void OnTimer()
  {
   // Poll REP socket
   ZmqMsg msg;
   if(socket_rep.recv(msg, true)) { // Non-blocking receive
      string req_str = msg.getData();
      if(req_str != "") {
         string rep_str = ProcessRequest(req_str);
         socket_rep.send(rep_str);
      }
   }
  }

//+------------------------------------------------------------------+
//| Request Processor                                                |
//+------------------------------------------------------------------+
string ProcessRequest(string req_json) {
   CJAVal req, resp;
   
   if(!req.Deserialize(req_json)) {
      resp["error"] = "INVALID_JSON";
      return resp.Serialize();
   }
   
   string action = req["action"].ToStr();
   
   if(action == "GET_ACCOUNT") {
      resp["balance"] = AccountInfoDouble(ACCOUNT_BALANCE);
      resp["equity"] = AccountInfoDouble(ACCOUNT_EQUITY);
      resp["margin"] = AccountInfoDouble(ACCOUNT_MARGIN);
      resp["free_margin"] = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   }
   else if(action == "GET_POSITIONS") {
      // Iterate positions
      int total = PositionsTotal();
      CJAVal positions_array;
      
      for(int i=0; i<total; i++) {
         ulong ticket = PositionGetTicket(i);
         if(ticket > 0) {
            CJAVal pos;
            pos["ticket"] = (long)ticket;
            pos["symbol"] = PositionGetString(POSITION_SYMBOL);
            pos["type"] = (long)PositionGetInteger(POSITION_TYPE);
            pos["volume"] = PositionGetDouble(POSITION_VOLUME);
            pos["price"] = PositionGetDouble(POSITION_PRICE_OPEN);
            pos["profit"] = PositionGetDouble(POSITION_PROFIT);
            positions_array.Add(pos);
         }
      }
      resp["positions"] = positions_array;
   }
   else if(action == "TRADE") {
      string symbol = req["symbol"].ToStr();
      string type_str = req["type"].ToStr();
      double volume = req["volume"].ToDbl();
      double sl = req["sl"].ToDbl();
      double tp = req["tp"].ToDbl();
      
      ENUM_ORDER_TYPE type = (type_str == "BUY") ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      
      trade.SetExpertMagicNumber(123456);
      
      bool res = false;
      if(type == ORDER_TYPE_BUY)
         res = trade.Buy(volume, symbol, 0, sl, tp, "ZMQ_ORDER");
      else
         res = trade.Sell(volume, symbol, 0, sl, tp, "ZMQ_ORDER");
         
      if(res) {
         resp["ticket"] = (long)trade.ResultOrder();
         resp["retcode"] = (long)trade.ResultRetcode();
      } else {
         resp["error"] = "TRADE_FAILED";
         resp["retcode"] = (long)trade.ResultRetcode();
      }
   }
   else if(action == "CLOSE") {
      ulong ticket = (ulong)req["ticket"].ToInt();
      if(trade.PositionClose(ticket)) {
         resp["status"] = "CLOSED";
      } else {
         resp["error"] = "CLOSE_FAILED";
      }
   }
   else {
      resp["error"] = "UNKNOWN_ACTION";
   }
   
   return resp.Serialize();
}
```

## 3. Configuration & Running

1.  **Open MT5**.
2.  Go to **Tools -> Options -> Expert Advisors**.
3.  Check **"Allow DLL imports"** (Critical for ZMQ).
4.  Open **MetaEditor** (F4).
5.  Create `ZmqServer.mq5` with the code above.
6.  **Compile** (F7). Ensure no errors.
7.  Return to MT5 Terminal.
8.  Drag **ZmqServer** from the Navigator onto a chart (e.g., EURUSD).
9.  Check the "Experts" tab in the "Toolbox" window. You should see:
    > `ZmqServer Initialized. Listening on REP: 5555 PUSH: 5556`

## 4. Troubleshooting

*   **"DLL loading is not allowed"**: Enable DLLs in Options.
*   **"Failed to bind..."**: Ensure ports 5555/5556 are not in use. Restart MT5.
*   **No Data on Python**: Ensure Python client is connecting to `localhost`.
