import customtkinter as ctk
from tkinter import simpledialog, filedialog, messagebox
import requests
import json
import threading
import os

DEFAULT_WIDTH = 600
DEFAULT_HEIGHT = 800

ctk.set_appearance_mode('dark')
ctk.set_default_color_theme('blue')


class GemmaChatApp(ctk.CTk):
    def __init__(self, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
        super().__init__()

        self.title('Gemma 4 Chat')
        self.geometry(f'{width}x{height}')
        self.minsize(550, 400)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- 데이터 및 상태 변수 초기화 ---
        self.server_url = "http://192.168.45.146:1234/v1/chat/completions"
        self.model_name = "gemma4"
        
        self.default_system_message = (
            "1. 당신은 모든 분야의 지식을 완벽하게 마스터하고, 사용자의 요구를 정확히 파악하여 맞춤형 해결책을 제시하는 최고의 다중 페르소나 AI 어시스턴트입니다. 자만하지 않고 확실하지 않거나 모르는 부분은 모른다고 답변합니다.\n"
            "2. 답변은 일반 텍스트 형식으로 작성하고, 초등학생의 지식 수준을 반영합니다.\n"
            "3. 답변은 핵심만 간결하게 하고, 5문장 이내를 기본 지침으로 하지만 많은 설명이 필요한 경우에는 추가 답변을 할 수 있습니다."
        )
        self.system_message = self.default_system_message
        self.chat_room_title = "이름없는 대화"
        self.conversation_history = []
        
        self.system_card_frame = None
        self.sidebar_visible = False
        self.message_count = 0
        
        # [스케일 하드코딩 변경 구역]
        self.current_scale = 1.0 
        
        # customtkinter 시스템 배율 동기화 및 반영
        ctk.set_widget_scaling(self.current_scale)
        ctk.set_window_scaling(self.current_scale)
        
        self.current_autosave_path = None
        self.is_generating = False

        self.create_sidebar()
        self.create_main_area()
        self.add_system_card_to_ui(self.system_message)
        
        # 최초 실행 시 높이 레이아웃 1회 연산
        self.update_all_textbox_heights()

    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#1e1e24")
        self.sidebar_frame.grid_rowconfigure(5, weight=1) 
        self.sidebar_frame.grid_columnconfigure(0, weight=1)

        self.server_btn = ctk.CTkButton(
            self.sidebar_frame, text=f"[서버] {self.server_url[:20]}...", 
            anchor="w", fg_color="transparent", hover_color="#2b2b36", command=self.change_server_url
        )
        self.server_btn.grid(row=0, column=0, padx=10, pady=(15, 5), sticky="ew")

        self.model_btn = ctk.CTkButton(
            self.sidebar_frame, text=f"[모델] {self.model_name}", 
            anchor="w", fg_color="transparent", hover_color="#2b2b36", command=self.change_model_name
        )
        self.model_btn.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        self.export_btn = ctk.CTkButton(self.sidebar_frame, text="대화 내보내기", anchor="w", fg_color="transparent", hover_color="#2b2b36", command=self.export_conversation)
        self.export_btn.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        self.import_btn = ctk.CTkButton(self.sidebar_frame, text="대화 불러오기", anchor="w", fg_color="transparent", hover_color="#2b2b36", command=self.import_conversation)
        self.import_btn.grid(row=3, column=0, padx=10, pady=5, sticky="ew")

        self.new_chat_btn = ctk.CTkButton(
            self.sidebar_frame, text="새 대화 시작", anchor="w",
            fg_color="transparent", hover_color="#2b2b36", command=self.clear_chat
        )
        self.new_chat_btn.grid(row=4, column=0, padx=10, pady=5, sticky="ew")

        self.scale_btn = ctk.CTkButton(
            self.sidebar_frame, text="GUI 스케일 변경", anchor="w",
            fg_color="transparent", hover_color="#2b2b36", command=self.change_gui_scaling
        )
        self.scale_btn.grid(row=6, column=0, padx=10, pady=(15, 15), sticky="ew")

    def change_gui_scaling(self):
        new_scale_str = simpledialog.askstring(
            "GUI 스케일 설정", 
            f"원하는 화면 배율을 소수로 입력하세요:\n예: 0.8(80%), 1.0(100%), 1.2(120%), 1.5(150%)\n현재 배율: {self.current_scale}", 
            initialvalue=str(self.current_scale)
        )
        
        if new_scale_str:
            try:
                factor = float(new_scale_str.strip())
                if 0.5 <= factor <= 3.0:
                    ctk.set_widget_scaling(factor)
                    ctk.set_window_scaling(factor)
                    self.current_scale = factor
                    self.update_all_textbox_heights()
                else:
                    messagebox.showwarning("범위 초과", "스케일 값은 0.5에서 3.0 사이여야 합니다.")
            except ValueError:
                messagebox.showerror("입력 에러", "유효한 숫자를 입력해 주세요.")

    def change_server_url(self):
        new_url = simpledialog.askstring("서버 주소 변경", "새로운 API 서버 주소를 입력하세요:", initialvalue=self.server_url)
        if new_url and new_url.strip():
            self.server_url = new_url.strip()
            display_url = self.server_url if len(self.server_url) <= 20 else f"{self.server_url[:20]}..."
            self.server_btn.configure(text=f"[서버] {display_url}")

    def change_model_name(self):
        new_model = simpledialog.askstring("모델 변경", "변경할 모델명을 입력하세요:", initialvalue=self.model_name)
        if new_model and new_model.strip():
            self.model_name = new_model.strip()
            self.model_btn.configure(text=f"[모델] {self.model_name}")

    def create_main_area(self):
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew")
        
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, minsize=55)
        self.main_container.grid_rowconfigure(1, weight=1)
        # 입력란 영역 높이를 5줄 텍스트박스에 맞춰 115 픽셀 정도로 확보
        self.main_container.grid_rowconfigure(2, minsize=115)

        self.create_header()
        self.create_content()
        self.create_input()

    def toggle_sidebar(self):
        if self.sidebar_visible:
            self.sidebar_frame.grid_forget()
            self.sidebar_visible = False
        else:
            self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
            self.sidebar_visible = True

    def create_header(self):
        self.header_frame = ctk.CTkFrame(self.main_container, corner_radius=0)
        self.header_frame.grid(row=0, column=0, sticky='nsew')
        
        self.header_frame.grid_columnconfigure(1, weight=1)
        self.header_frame.grid_columnconfigure(2, weight=0)

        # [요청 반영] Pydroid3 터미널 폰트에서도 절대 깨지지 않는 수학용 합동 기호 '≡' (삼선 형태) 적용
        self.menu_button = ctk.CTkButton(self.header_frame, text='≡', font=('Arial', 18, 'bold'), width=40, command=self.toggle_sidebar)
        self.menu_button.grid(row=0, column=0, padx=10, pady=8)

        self.room_label = ctk.CTkLabel(
            self.header_frame, text=self.chat_room_title, font=('Arial', 15, 'bold'), cursor="hand2"
        )
        self.room_label.grid(row=0, column=1, sticky='w', padx=5)
        self.room_label.bind("<Button-1>", self.rename_chat_room)

        controls_pack = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        controls_pack.grid(row=0, column=2, padx=10, pady=5, sticky="e")

        temp_label = ctk.CTkLabel(controls_pack, text="Temp:", font=('Arial', 11))
        temp_label.pack(side="left", padx=(5, 2))

        self.temp_value_label = ctk.CTkLabel(controls_pack, text="0.7", font=('Arial', 11, 'bold'), width=24)
        
        def update_temp_label(val):
            rounded_val = round(float(val), 1)
            self.slider.set(rounded_val)
            self.temp_value_label.configure(text=str(rounded_val))

        self.slider = ctk.CTkSlider(controls_pack, from_=0.0, to=2.0, width=100, number_of_steps=20, command=update_temp_label)
        self.slider.set(0.7)
        self.slider.pack(side="left", padx=2)
        self.temp_value_label.pack(side="left", padx=(0, 10))

        self.think_var = ctk.BooleanVar(value=False)
        self.think_cb = ctk.CTkCheckBox(controls_pack, text="Thinking", variable=self.think_var, font=('Arial', 11), width=70)
        self.think_cb.pack(side="left", padx=5)

        self.system_mode_var = ctk.BooleanVar(value=False)
        self.system_cb = ctk.CTkCheckBox(controls_pack, text="System", variable=self.system_mode_var, font=('Arial', 11), text_color="#e67e22", width=65)
        self.system_cb.pack(side="left", padx=5)

        header_line = ctk.CTkFrame(self.main_container, height=1, fg_color="#3a3a44")
        header_line.grid(row=0, column=0, sticky="ew", pady=(50, 0))

    def rename_chat_room(self, event=None):
        new_title = simpledialog.askstring("대화방 이름 변경", "새로운 대화방 이름을 입력하세요:", initialvalue=self.chat_room_title)
        if new_title and new_title.strip():
            self.chat_room_title = new_title.strip()
            self.room_label.configure(text=self.chat_room_title)
            self.current_autosave_path = None
            self.trigger_background_autosave()

    def create_content(self):
        self.chat_scroll_frame = ctk.CTkScrollableFrame(self.main_container, corner_radius=0, fg_color="transparent")
        self.chat_scroll_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        self.chat_scroll_frame.grid_columnconfigure(0, weight=1)
        self.chat_scroll_frame.bind("<Configure>", lambda e: self.update_all_textbox_heights())

    def create_input(self):
        self.input_frame = ctk.CTkFrame(self.main_container, corner_radius=0)
        self.input_frame.grid(row=2, column=0, sticky='nsew')
        # 행은 0번 하나만 사용하고 버튼과 텍스트박스가 동일한 높이를 가지도록 함
        self.input_frame.grid_rowconfigure(0, weight=1)
        self.input_frame.grid_columnconfigure(0, weight=1)
        self.input_frame.grid_columnconfigure(1, weight=0)

        # 입력 창 높이 100
        self.input_text = ctk.CTkTextbox(self.input_frame, height=100)
        self.input_text.grid(row=0, column=0, sticky='nsew', padx=(10, 5), pady=8)

        self.input_text.bind("<Return>", self.handle_enter_key)

        # [수정] sticky='nsew'를 적용하여 위아래로 높이를 꽉 채우게 설정
        self.send_button = ctk.CTkButton(self.input_frame, text='전송', width=70, height=100, command=self.send_message)
        self.send_button.grid(row=0, column=1, padx=(5, 10), pady=8, sticky="nsew")

    def handle_enter_key(self, event):
        if event.state & 0x0001:  
            return None           
        else:
            if not self.is_generating:
                self.send_message()   
            return "break"        

    def scroll_to_bottom(self):
        self.after(20, lambda: self.chat_scroll_frame._parent_canvas.yview_moveto(1.0))

    def update_scroll_region(self):
        try:
            self.chat_scroll_frame._parent_canvas.configure(
                scrollregion=self.chat_scroll_frame._parent_canvas.bbox("all")
            )
        except Exception:
            pass

    def clear_chat(self):
        if self.is_generating:
            return
        
        has_dialogue = any(msg["type"] == "dialogue_set" for msg in self.conversation_history)
        if has_dialogue:
            ans = messagebox.askyesno("기존 대화 저장", "새 대화를 시작하기 전에 현재 대화 내용을 수동 파일로 저장하시겠습니까?")
            if ans:
                self.export_conversation()

        for item in self.conversation_history:
            item["frame"].destroy()
        self.conversation_history.clear()
        self.chat_room_title = "이름없는 대화"
        self.room_label.configure(text=self.chat_room_title)
        
        self.system_message = self.default_system_message
        self.system_card_frame = None
        self.current_autosave_path = None
        self.think_var.set(False)
        
        self.add_system_card_to_ui(self.system_message)

    def pack_current_data(self):
        export_data = {
            "room_title": self.chat_room_title,
            "system_message": self.system_message,
            "temperature": self.slider.get(),
            "enable_thinking": self.think_var.get(),
            "history": []
        }
        for msg in self.conversation_history:
            if msg["type"] == "system":
                raw_text = msg["textbox_widget"].get("1.0", "end-1c")
                export_data["history"].append({
                    "type": "system",
                    "text": raw_text.replace("[System Prompt]\n", ""),
                    "is_active": msg["state"]["is_active"]
                })
            elif msg["type"] == "dialogue_set":
                combined_text = msg["integrated_textbox"].get("1.0", "end-1c")
                user_part = ""
                agent_part = ""
                
                if "[User]\n" in combined_text and "\n[Agent]\n" in combined_text:
                    parts = combined_text.split("\n[Agent]\n")
                    user_part = parts[0].replace("[User]\n", "")
                    agent_part = parts[1]
                else:
                    user_part = msg["user_text"]
                    agent_part = combined_text.replace("[Agent]\n", "")
                    
                export_data["history"].append({
                    "type": "dialogue_set",
                    "user_text": user_part,
                    "agent_text": agent_part,
                    "is_active": msg["state"]["is_active"]
                })
        return export_data

    def trigger_background_autosave(self):
        if not self.conversation_history:
            return
        save_data = self.pack_current_data()
        
        if not self.current_autosave_path:
            base_name = f"{self.chat_room_title}_자동저장"
            filename = f"{base_name}.txt"
            counter = 1
            while os.path.exists(filename):
                filename = f"{base_name}({counter}).txt"
                counter += 1
            self.current_autosave_path = filename

        def save_worker(path, data):
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                print(f"[Auto-save Error]: {e}")

        threading.Thread(target=save_worker, args=(self.current_autosave_path, save_data), daemon=True).start()

    def export_conversation(self):
        if not self.conversation_history:
            return

        file_path = filedialog.asksaveasfilename(
            initialfile=f"{self.chat_room_title}.txt",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        export_data = self.pack_current_data()
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            messagebox.showerror("오류", f"파일 저장에 실패했습니다:\n{e}")

    def import_conversation(self):
        if self.is_generating:
            return
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                import_data = json.load(f)
        except Exception as e:
            return

        for item in self.conversation_history:
            item["frame"].destroy()
        self.conversation_history.clear()
        self.system_card_frame = None

        self.chat_room_title = import_data.get("room_title", "불러온 대화")
        self.room_label.configure(text=self.chat_room_title)
        self.system_message = import_data.get("system_message", "")
        
        self.slider.set(import_data.get("temperature", 0.7))
        self.temp_value_label.configure(text=str(round(self.slider.get(), 1)))
        self.think_var.set(import_data.get("enable_thinking", False))
        
        if "_자동저장" in file_path:
            self.current_autosave_path = file_path
        else:
            self.current_autosave_path = None

        saved_history = import_data.get("history", [])
        for block in saved_history:
            if block["type"] == "system":
                self.add_system_card_to_ui(block["text"])
                if not block.get("is_active", True):
                    for item in self.conversation_history:
                        if item["type"] == "system":
                            item["frame"].winfo_children()[0].winfo_children()[1].invoke()
                            break
            elif block["type"] == "dialogue_set":
                u_text = block["user_text"]
                a_text = block["agent_text"]
                
                t_box, a_state, a_frame = self.add_dialogue_set_card(u_text, a_text)
                self.conversation_history.append({
                    "type": "dialogue_set",
                    "user_text": u_text,
                    "integrated_textbox": t_box,
                    "state": a_state,
                    "frame": a_frame
                })
                
                if not block.get("is_active", True):
                    card_container = a_frame.winfo_children()[0]
                    for child in card_container.winfo_children():
                        if isinstance(child, ctk.CTkButton) and child.cget("text") == "비활성":
                            child.invoke()
                            break
        self.update_all_textbox_heights()
        self.scroll_to_bottom()

    def resize_textbox_globally(self, textbox, max_height=120):
        def _execute_resize():
            try:
                num_lines = int(textbox._textbox.index('end-1c').split('.')[0])
                font_metrics = textbox._textbox.tk.call('font', 'metrics', textbox._textbox.cget('font'))
                line_height = int(font_metrics.split('-linespace ')[1].split()[0])
                
                calculated_pixel_height = (num_lines * line_height) + 25
                
                if calculated_pixel_height > max_height:
                    textbox.configure(height=max_height)
                else:
                    textbox.configure(height=calculated_pixel_height)
                
                self.update_scroll_region()
            except Exception:
                pass
        self.after(1, _execute_resize)

    def update_all_textbox_heights(self):
        for item in self.conversation_history:
            if item["type"] == "system":
                self.resize_textbox_globally(item["textbox_widget"])
            elif item["type"] == "dialogue_set":
                self.resize_textbox_globally(item["integrated_textbox"])

    def add_system_card_to_ui(self, text):
        item_frame = ctk.CTkFrame(self.chat_scroll_frame, fg_color="transparent")
        item_frame.grid(row=self.message_count, column=0, sticky="ew", padx=10, pady=5)
        item_frame.grid_columnconfigure(0, weight=1)

        orange_bg = "#e67e22"
        inactive_bg = "#2c2c35"
        
        card_frame = ctk.CTkFrame(item_frame, fg_color=orange_bg, corner_radius=10)
        card_frame.grid(row=0, column=0, sticky="nsew")
        card_frame.grid_columnconfigure(0, weight=1)

        txt_box = ctk.CTkTextbox(
            card_frame, height=50,
            fg_color="transparent", border_width=0, activate_scrollbars=True,
            font=('Arial', 14, 'bold'), text_color="#ffffff"
        )
        txt_box.grid(row=0, column=0, padx=12, pady=8, sticky="ew")
        txt_box.insert("1.0", f"[System Prompt]\n{text}")
        txt_box.configure(state="disabled")

        state = {"is_active": True}

        def toggle_active():
            if state["is_active"]:
                card_frame.configure(fg_color=inactive_bg)
                txt_box.configure(text_color="#666666")
                toggle_button.configure(text="활성", fg_color="#555555")
                delete_button.configure(state="normal", fg_color="#c0392b")
                state["is_active"] = False
            else:
                card_frame.configure(fg_color=orange_bg)
                txt_box.configure(text_color="#ffffff")
                toggle_button.configure(text="비활성", fg_color="#444444")
                delete_button.configure(state="disabled", fg_color="#555555")
                state["is_active"] = True
            self.trigger_background_autosave()

        def delete_card():
            if getattr(self, 'system_card_frame', None) == item_frame:
                self.system_message = ""
                self.system_card_frame = None
            for item in self.conversation_history:
                if item["frame"] == item_frame:
                    self.conversation_history.remove(item)
                    break
            item_frame.destroy()
            self.update_scroll_region()
            self.trigger_background_autosave()

        toggle_button = ctk.CTkButton(card_frame, text="비활성", width=50, height=24, font=('Arial', 11), fg_color="#444444", command=toggle_active)
        toggle_button.grid(row=0, column=1, padx=5, pady=8, sticky="e")

        delete_button = ctk.CTkButton(card_frame, text="X", width=24, height=24, font=('Arial', 11, 'bold'), state="disabled", fg_color="#555555", hover_color="#962d22", command=delete_card)
        delete_button.grid(row=0, column=2, padx=(5, 10), pady=8, sticky="e")

        sep = ctk.CTkFrame(item_frame, height=1, fg_color="#444444")
        sep.grid(row=1, column=0, sticky="ew", pady=(8, 2))

        self.system_card_frame = item_frame
        self.conversation_history.insert(0, {
            "type": "system", 
            "textbox_widget": txt_box, 
            "state": state, 
            "frame": item_frame
        })
        
        self.message_count += 1
        self.resize_textbox_globally(txt_box)
        self.scroll_to_bottom()

    def add_dialogue_set_card(self, user_text, initial_agent_text="생각 중..."):
        item_frame = ctk.CTkFrame(self.chat_scroll_frame, fg_color="transparent")
        item_frame.grid(row=self.message_count, column=0, sticky="ew", padx=10, pady=5)
        item_frame.grid_columnconfigure(0, weight=1)

        card_color = "#2c3e50"
        inactive_bg = "#2b2b2b"
        
        card_frame = ctk.CTkFrame(item_frame, fg_color=card_color, corner_radius=10)
        card_frame.grid(row=0, column=0, sticky="nsew")
        card_frame.grid_columnconfigure(0, weight=1)

        total_content = f"[User]\n{user_text}\n[Agent]\n{initial_agent_text}"
        
        integrated_box = ctk.CTkTextbox(
            card_frame, height=60,
            fg_color="transparent", border_width=0, activate_scrollbars=True,
            font=('Arial', 14), text_color="#ffffff"
        )
        integrated_box.grid(row=0, column=0, padx=15, pady=12, sticky="ew")
        integrated_box.insert("1.0", total_content)
        integrated_box.configure(state="disabled")

        state = {"is_active": True}

        def toggle_active():
            if state["is_active"]:
                card_frame.configure(fg_color=inactive_bg)
                integrated_box.configure(text_color="#666666")
                toggle_button.configure(text="활성", fg_color="#555555")
                delete_button.configure(state="normal", fg_color="#c0392b")
                state["is_active"] = False
            else:
                card_frame.configure(fg_color=card_color)
                integrated_box.configure(text_color="#ffffff")
                toggle_button.configure(text="비활성", fg_color="#444444")
                delete_button.configure(state="disabled", fg_color="#555555")
                state["is_active"] = True
            self.trigger_background_autosave()

        def delete_card():
            for item in self.conversation_history:
                if item["frame"] == item_frame:
                    self.conversation_history.remove(item)
                    break
            item_frame.destroy()
            self.update_scroll_region()
            self.trigger_background_autosave()

        toggle_button = ctk.CTkButton(card_frame, text="비활성", width=50, height=24, font=('Arial', 11), fg_color="#444444", command=toggle_active)
        toggle_button.grid(row=0, column=1, padx=5, pady=8, sticky="ne")

        delete_button = ctk.CTkButton(card_frame, text="X", width=24, height=24, font=('Arial', 11, 'bold'), state="disabled", fg_color="#555555", hover_color="#962d22", command=delete_card)
        delete_button.grid(row=0, column=2, padx=(5, 10), pady=8, sticky="ne")

        separator = ctk.CTkFrame(item_frame, height=1, fg_color="#444444")
        separator.grid(row=1, column=0, sticky="ew", pady=(8, 2))

        self.message_count += 1
        self.resize_textbox_globally(integrated_box)
        self.scroll_to_bottom()

        return integrated_box, state, item_frame

    def send_message(self):
        if self.is_generating:
            return

        user_text = self.input_text.get("1.0", "end-1c").strip()
        if not user_text:
            return

        if self.system_mode_var.get():
            self.system_message = user_text
            self.input_text.delete("1.0", "end")
            self.system_mode_var.set(False)
            
            if self.system_card_frame:
                for item in self.conversation_history:
                    if item["frame"] == self.system_card_frame:
                        t_box = item["textbox_widget"]
                        t_box.configure(state="normal")
                        t_box.delete("1.0", "end")
                        t_box.insert("1.0", f"[System Prompt]\n{self.system_message}")
                        t_box.configure(state="disabled")
                        self.resize_textbox_globally(t_box)
                        break
            else:
                self.add_system_card_to_ui(self.system_message)
            self.trigger_background_autosave()
            return

        self.is_generating = True
        self.send_button.configure(state="disabled", text="응답중")

        self.input_text.delete("1.0", "end")
        t_box, a_state, a_frame = self.add_dialogue_set_card(user_text, "생각 중...")
        
        self.conversation_history.append({
            "type": "dialogue_set",
            "user_text": user_text,
            "integrated_textbox": t_box,
            "state": a_state,
            "frame": a_frame
        })

        threading.Thread(target=self.fetch_llm_stream_response, args=(t_box, user_text), daemon=True).start()

    def fetch_llm_stream_response(self, target_box, user_text):
        api_messages = []
        
        if self.system_message:
            system_active = True
            for msg in self.conversation_history:
                if msg["type"] == "system" and not msg["state"]["is_active"]:
                    system_active = False
                    break
            if system_active:
                api_messages.append({"role": "system", "content": self.system_message})
            
        for msg in self.conversation_history:
            if msg["type"] == "dialogue_set" and msg["state"]["is_active"]:
                api_messages.append({"role": "user", "content": msg["user_text"]})
                
                combined = msg["integrated_textbox"].get("1.0", "end-1c")
                agent_content = ""
                if "\n[Agent]\n" in combined:
                    agent_content = combined.split("\n[Agent]\n")[1]
                else:
                    agent_content = combined.replace("[Agent]\n", "")
                
                if agent_content == "생각 중...":
                    agent_content = ""
                
                if agent_content:
                    api_messages.append({"role": "assistant", "content": agent_content})

        payload = {
            "model": self.model_name,
            "messages": api_messages,
            "stream": True,
            "temperature": float(self.slider.get()),
            "chat_template_kwargs": {
                "enable_thinking": bool(self.think_var.get())
            }
        }

        headers = {'Content-Type': 'application/json'}
        full_response_text = ""

        try:
            response = requests.post(self.server_url, headers=headers, json=payload, stream=True, timeout=15)
            
            if response.status_code != 200:
                def set_err():
                    target_box.configure(state="normal")
                    target_box.delete("1.0", "end")
                    target_box.insert("1.0", f"[User]\n{user_text}\n\n[Agent]\n에러 발생 (Status Code: {response.status_code})")
                    target_box.configure(state="disabled")
                    self.resize_textbox_globally(target_box)
                    self.is_generating = False
                    self.send_button.configure(state="normal", text="전송")
                self.after(0, set_err)
                return

            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8').strip()
                    if decoded_line.startswith("data: "):
                        json_str = decoded_line[6:]
                        if json_str == "[DONE]":
                            self.trigger_background_autosave()
                            break
                        try:
                            chunk = json.loads(json_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            if "content" in delta:
                                token = delta["content"]
                                full_response_text += token
                                
                                def update_ui(t=full_response_text):
                                    target_box.configure(state="normal")
                                    combined_output = f"[User]\n{user_text}\n\n[Agent]\n{t}"
                                    target_box.delete("1.0", "end")
                                    target_box.insert("1.0", combined_output)
                                    target_box.configure(state="disabled")
                                    
                                    self.resize_textbox_globally(target_box)
                                
                                self.after(0, update_ui)
                                self.after(0, self.scroll_to_bottom)
                        except json.JSONDecodeError:
                            continue

        except requests.exceptions.RequestException as e:
            def set_fail():
                target_box.configure(state="normal")
                target_box.delete("1.0", "end")
                target_box.insert("1.0", f"[User]\n{user_text}\n\n[Agent]\n서버 연결 실패:\n{str(e)}")
                target_box.configure(state="disabled")
                self.resize_textbox_globally(target_box)
            self.after(0, set_fail)

        finally:
            def unlock_ui():
                self.is_generating = False
                self.send_button.configure(state="normal", text="전송")
            self.after(0, unlock_ui)


if __name__ == '__main__':
    app = GemmaChatApp()
    app.mainloop()