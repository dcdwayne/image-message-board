document.addEventListener("DOMContentLoaded", () => {
    const postForm = document.getElementById("postForm");
    const feedContainer = document.getElementById("feedContainer");

    // 處理表單送出
    postForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const textContent = document.getElementById("textContent").value;
        const imageFile = document.getElementById("imageFile").files[0];

        // 使用 FormData 打包文字與圖片檔案
        const formData = new FormData();
        formData.append("text", textContent);
        formData.append("image", imageFile);

        try {
            // 呼叫後端新增 API
            const response = await fetch("/api/posts", {
                method: "POST",
                body: formData
            });
            const result = await response.json();
            
            if(response.ok && result.ok) {
                // 上傳成功，重新抓取並渲染所有留言
                loadPosts();
                postForm.reset();
            } else {
                alert("上傳失敗: " + (result.detail || "未知錯誤"));
            }

        } catch (error) {
            console.error("上傳失敗:", error);
            alert("上傳失敗，請檢查網路連線或後端設定");
        }
    });

    // 載入並顯示所有留言
    async function loadPosts() {
        try {
            // 正式呼叫後端取得 API
            const response = await fetch("/api/posts");
            const data = await response.json();
            
            feedContainer.innerHTML = ""; // 清空現有列表
            
            // 遍歷後端回傳的資料，並正確傳入 id
            data.forEach(post => {
                renderPost(post.id, post.text, post.imageUrl);
            });
            
        } catch (error) {
            console.error("載入留言失敗:", error);
        }
    }

    // 建立留言卡片的 DOM 結構
    function renderPost(id, text, imageUrl, prepend = false) {
        const card = document.createElement("div");
        card.className = "post-card";
        card.dataset.id = id; // 將資料庫 id 綁定在 DOM 上

        // 建立刪除按鈕
        const deleteBtn = document.createElement("button");
        deleteBtn.className = "delete-btn";
        deleteBtn.innerHTML = "&times;"; // HTML 的 X 符號
        deleteBtn.title = "刪除此留言";
        
        // 綁定刪除事件
        deleteBtn.addEventListener("click", async () => {
            if(confirm("確定要刪除這篇留言與圖片嗎？")) {
                try {
                    // 呼叫 DELETE API
                    const response = await fetch(`/api/posts/${id}`, {
                        method: "DELETE"
                    });
                    const result = await response.json();
                    
                    if(result.ok) {
                        card.remove(); // 從畫面上移除
                    } else {
                        alert("刪除失敗");
                    }
                } catch(e) {
                    console.error(e);
                }
            }
        });

        const textDiv = document.createElement("div");
        textDiv.className = "post-text";
        textDiv.textContent = text;

        const img = document.createElement("img");
        img.className = "post-image";
        img.src = imageUrl;
        img.alt = "使用者上傳的圖片";

        // 記得把按鈕加進卡片裡
        card.appendChild(deleteBtn);
        card.appendChild(textDiv);
        card.appendChild(img);

        if (prepend) {
            feedContainer.prepend(card); // 新留言放最上面
        } else {
            feedContainer.appendChild(card);
        }
    }

    // 頁面載入時先抓取一次留言列表
    loadPosts();
});