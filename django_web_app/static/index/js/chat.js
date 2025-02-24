const query = (obj) =>
  Object.keys(obj)
    .map((k) => encodeURIComponent(k) + "=" + encodeURIComponent(obj[k]))
    .join("&");
const colorThemes = document.querySelectorAll('[name="theme"]');
//const markdown = window.markdownit();
//katex解析公式
const markdown = markdownit({html:true})
                      .use(texmath, { engine: katex,
                                      delimiters: 'dollars',
                                      katexOptions: {} } );
const message_box = document.getElementById(`messages`);
const message_input = document.getElementById(`message-input`);
const box_conversations = document.querySelector(`.top`);
const spinner = box_conversations.querySelector(".spinner");
const stop_generating = document.querySelector(`.stop_generating`);
const send_button = document.querySelector(`#send-button`);
let prompt_lock = false;
let uploadedImages = []; // 临时存储上传的图片地址

// 使用此函数获取北京时间
const beijingTime = getBeijingTime();

hljs.addPlugin(new CopyButtonPlugin());

let cropper;
// 上传图片预览功能

function reinit()
{
 document.querySelector('.upload-icon').classList.remove('disabled-upload');
}
function hideCropper() {
    if (cropper) {
        cropper.destroy();
        cropper = null;
    }
    document.getElementById('image-cropper-container').style.display = 'none';
}

function triggerFileInput() {
    const fileInput = document.getElementById('file-input');
    fileInput.click();
}

function previewImage(inputOrBlob) {
    let blob;

    if (inputOrBlob instanceof Blob) {
        blob = inputOrBlob;
    } else if (inputOrBlob.files && inputOrBlob.files[0]) {
        blob = inputOrBlob.files[0];
    } else {
        return; // 如果不是Blob或文件输入，直接返回
    }

    const reader = new FileReader();

    reader.onload = function (e) {
        const imagePreview = document.getElementById('image-preview');
        imagePreview.src = e.target.result;

        if (cropper) {
            cropper.destroy();
            cropper = null;
        }

        // 初始化Cropper.js
        cropper = new Cropper(imagePreview, {
            viewMode: 1,
            ready: function() {
                // 获取图片的原始尺寸
                const imageData = this.cropper.getImageData();
                const originalWidth = imageData.naturalWidth;
                const originalHeight = imageData.naturalHeight;

                // // 计算裁剪框的初始尺寸（原图片尺寸的一半）
                // const cropWidth = originalWidth * 0.3;
                // const cropHeight = originalHeight * 0.3;
                //
                // // 计算裁剪框的初始位置（居中）
                // const offsetX = (originalWidth - cropWidth) / 3;
                // const offsetY = (originalHeight - cropHeight) / 3;
                //
                // // 设置裁剪框的尺寸和位置
                // this.cropper.setData({
                //     x: offsetX,
                //     y: offsetY,
                //     width: cropWidth,
                //     height: cropHeight
                // });
                this.cropper.setDragMode('move');
            },
            zoom: function(event) {
                // 防止放大超出原始尺寸
                if (event.detail.ratio > 1) {
                    event.preventDefault();
                    this.cropper.zoomTo(1);
                }
            }
        });

        document.getElementById('image-cropper-container').style.display = 'block';
        // 禁用上传按钮
        document.querySelector('.upload-icon').classList.add('disabled-upload');
        document.getElementById('messages').scrollTop = 0;

        // 当需要将裁剪的结果发送到服务器时
        document.getElementById('confirm-crop').addEventListener('click', function() {
            cropAndSendImage();
            hideCropper();
        });

        document.getElementById('cancel-crop').addEventListener('click', function() {
            hideCropper();

        document.querySelector('.upload-icon').classList.remove('disabled-upload');
        });
    }

    reader.readAsDataURL(blob);
}
// GPT4 image container
function appendToImagePreviewContainer(imagePath,relative_path) {
    // 创建图片容器
    const imageContainer = document.createElement('div');
    imageContainer.classList.add('image-preview-item-container');

    // 创建图片元素
    const img = document.createElement('img');
    img.src = imagePath;
    img.alt = 'Uploaded Image';
    img.classList.add('image-preview-item');

    // 创建删除图标
    const deleteIcon = document.createElement('span');
    deleteIcon.classList.add('delete-icon');
    deleteIcon.innerHTML = '&times;'; // 使用 HTML 实体 × 表示删除
    // 删除处理
    deleteIcon.onclick = function() {
    // 发送删除请求到服务器的URL
    const data = { file_path: imagePath}; // 可能需要其他标识文件的信息
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute("content");
    // 使用fetch API发送DELETE请求
    fetch('/post/gpt4/image/delete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            // 如果需要的话添加 CSRF token
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        if (response.ok) {
            // 如果服务器端文件删除成功，也删除前端的图片元素
            imageContainer.remove();
            const index = uploadedImages.indexOf(relative_path);
            if (index > -1) {
                uploadedImages.splice(index, 1); // 删除数组中的元素
            }

        } else {
            // 如果出现错误，你可能想要通知用户
            alert('文件删除失败。');
        }
    })
    .catch(error => {
        // 处理网络错误或其他错误
        console.error('删除文件时出现错误:', error);
        alert('删除文件时出现错误。');
    });
};

    // 将图片和删除图标添加到容器中
    imageContainer.appendChild(img);
    imageContainer.appendChild(deleteIcon);

    // 获取预览容器并将新创建的图片容器添加进去
    const container = document.getElementById('image-preview-container');
    container.appendChild(imageContainer);
    container.style.display = 'flex';
}


// 登录按钮隐藏
document.addEventListener('DOMContentLoaded', async function() {
    let cloudDataButton = document.getElementById('cloudDataButton');
    let loginURL = cloudDataButton.getAttribute('data-login-url');

    let loggedIn = await isUserLoggedIn();
    if (loggedIn) {
        cloudDataButton.style.display = "none";  // Hide the button for logged-in users
    } else {
        cloudDataButton.addEventListener('click', function() {
            window.location.href = loginURL;
        });
    }
});

// 只允许登录的用户访问4.0
async function setupModelDropdown() {
    let loggedIn = await isUserLoggedIn();

    let modelDropdown = document.getElementById('model');
    let gpt4Option = document.querySelector('#model option[value="gpt-4o"]');
    let gpt4VisionOption = document.querySelector('#model option[value="gpt-4-turbo"]');
    if (!loggedIn && gpt4Option && gpt4VisionOption) {
        gpt4Option.disabled = true;
        gpt4VisionOption.disabled = true;
    }
}
// Call this function when the document is loaded
document.addEventListener('DOMContentLoaded', function() {
    setupModelDropdown();
});

// 允许直接粘贴图片
document.getElementById('message-input').addEventListener('paste', function(e) {
    let clipboardData = e.clipboardData || window.clipboardData;
    let items = clipboardData.items;

    for (let i = 0; i < items.length; i++) {
        // 如果是图片内容
        if (items[i].type.indexOf('image') !== -1) {
            let blob = items[i].getAsFile();

            // 用你的函数处理这个图片
            previewImage(blob);  // 现在可以直接使用 previewImage
            e.preventDefault(); // 防止图片内容被粘贴到文本框中
            break; // 停止循环
        }
    }
});

function cropAndSendImage() {
    const gpt4VisionOption = document.querySelector('#model option[value="gpt-4-turbo"]');
      let gpt4Option = document.querySelector('#model option[value="gpt-4o"]');
    const modal = document.getElementById('loading-modal');
    const modalMessage = document.getElementById('modal-message');
    const modalClose = document.querySelector('.modal-close');

    const MAX_SIZE = 1 * 1024 * 1024; // 图片最大1MB

    modalClose.onclick = function() {
        modal.style.display = "none";
    }

    if (cropper && (gpt4VisionOption.selected || gpt4Option.selected)) {
        // 获取裁剪后的canvas
        const canvas = cropper.getCroppedCanvas();
        // 提交form要csrfToken
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

        modal.style.display = "block"; // 显示模态对话框
        modalMessage.textContent = "图片上传中..."; // 设置上传消息

        // 将canvas转换为blob
        canvas.toBlob(function(blob) {
            const formData = new FormData();
            formData.append('croppedImage', blob, 'cropped.png');
            formData.append('conversation_id', window.conversation_id);

            // 发送裁剪后的图片到后端
            // 发送裁剪后的图片到后端
            fetch('/post/gpt4/image', { // 替换为实际的上传URL
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrfToken
                },
            })
            .then(response => response.json())
            .then(data => {
               console.log('Upload successful:', data);
               modalMessage.textContent = "上传成功!"; // 设置成功消息
                // 显示图片存储地址
                //alert(`图片已存储在: ${data.file_path}`);
                 // 将新的图片地址添加到数组中
                uploadedImages.push(data.relative_path);
                appendToImagePreviewContainer(data.file_path,data.relative_path); // 使用上传后的图片路径更新预览容器

                document.querySelector('.upload-icon').classList.remove('disabled-upload');
                modal.style.display = "none"; // 关闭模态对话框
            })
            .catch(error => {
                console.error('Upload failed:', error);
                modalMessage.textContent = "上传失败"; // 设置失败消息
                modal.style.display = "none"; // 关闭模态对话框
            });
        }, 'image/jpeg',0.7);
    }
    else if(cropper) {
        // 获取裁剪后的canvas
        const canvas = cropper.getCroppedCanvas();
        // 提交form要csrfToken
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

        modal.style.display = "block"; // 显示模态对话框
        modalMessage.textContent = "文本转换中..."; // 设置上传消息

        // 将canvas转换为blob
        canvas.toBlob(function(blob) {
            const formData = new FormData();
            formData.append('croppedImage', blob, 'cropped.png');

            // 发送裁剪后的图片到后端
            fetch('/post/gptchat/image', { // 替换为实际的上传URL
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrfToken
                },
            })
            .then(response => response.json())
            .then(data => {
               console.log('Upload successful:', data);
               modalMessage.textContent = "转换成功!"; // 设置成功消息
                // 获取文本框 DOM 元素
                const textareaElem = document.getElementById('message-input');

                // 更新文本框的内容
                textareaElem.value += data.extracted_text;

                document.querySelector('.upload-icon').classList.remove('disabled-upload');
                modal.style.display = "none"; // 显示模态对话框
            })
            .catch(error => {
                console.error('Upload failed:', error);
                modalMessage.textContent = "文本识别识别"; // 设置失败消息
                modal.style.display = "none"; // 显示模态对话框
            });
        }, 'image/jpeg',0.7);
    }
}

function resizeTextarea(textarea) {
  textarea.style.height = '80px';
  textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
}

const format = (text) => {
  return text.replace(/(?:\r\n|\r|\n)/g, "<br>");
};

message_input.addEventListener("blur", () => {
  window.scrollTo(0, 0);
});

message_input.addEventListener("focus", () => {
  document.documentElement.scrollTop = document.documentElement.scrollHeight;
});

const delete_conversations = async () => {
  localStorage.clear();
  await new_conversation();
};

const handle_ask = async () => {
  message_input.style.height = `80px`;
  message_input.focus();

  window.scrollTo(0, 0);
  let message = message_input.value;

  if (message.length > 0 || uploadedImages.length > 0) {
    message_input.value = ``;
    await ask_gpt(message);
  }
};

const remove_cancel_button = async () => {
  stop_generating.classList.add(`stop_generating-hiding`);

  setTimeout(() => {
    stop_generating.classList.remove(`stop_generating-hiding`);
    stop_generating.classList.add(`stop_generating-hidden`);
  }, 300);
};

async function isUserLoggedIn() {
    try {
        const response = await fetch('/check-user-status/');
        const data = await response.json();

        if (data.status === 'logged_in') {
            return true;
        } else {
            return false;
        }
    } catch (error) {
        console.error("Error checking user login status:", error);
        return false;
    }
}

const ask_gpt = async (message) => {
    try {
        document.querySelector('.upload-icon').classList.add('disabled-upload');

        message_input.value = ``;
        message_input.innerHTML = ``;
        message_input.innerText = ``;

        add_conversation(window.conversation_id, message.substr(0, 20));
        window.scrollTo(0, 0);
        window.controller = new AbortController();

        jailbreak = document.getElementById("jailbreak");
        model = document.getElementById("model");
        prompt_lock = true;
        window.text = ``;
        window.token = message_id();

        stop_generating.classList.remove(`stop_generating-hidden`);

        let imagesHtml = '';
        // 如果 uploadedImages 数组有数据，生成图片的HTML
        if (uploadedImages.length > 0) {
            imagesHtml = `<div class="images-container-message">` + uploadedImages.map(imagePath => {
                // imagePath should be a relative path
                return `<div class="image-wrapper"><img src="/media/${imagePath}" alt="Uploaded Image" class="image-preview-message"></div>`;
            }).join('') + `</div>`;
        }


        // 消息的HTML结构，包含了图片和文本内容
        const messageHtml = `
        <div class="message">
            <div class="user">
                ${user_image}
                <i class="fa-regular fa-phone-arrow-up-right"></i>
            </div>
            <div class="content" id="user_${token}"> 
                ${imagesHtml} <!-- 这里插入图片 -->
                ${format(message)}
            </div>
        </div>
    `;

        // 插入到 message_box 中
        message_box.innerHTML += messageHtml;

        /* .replace(/(?:\r\n|\r|\n)/g, '<br>') */

        message_box.scrollTop = message_box.scrollHeight;
        window.scrollTo(0, 0);
        await new Promise((r) => setTimeout(r, 500));
        window.scrollTo(0, 0);

        message_box.innerHTML += `
            <div class="message">
                <div class="user">
                    ${gpt_image} <i class="fa-regular fa-phone-arrow-down-left"></i>
                </div>
                <div class="content" id="gpt_${window.token}">
                    <div id="cursor"></div>
                </div>
            </div>
        `;

        message_box.scrollTop = message_box.scrollHeight;
        window.scrollTo(0, 0);
        await new Promise((r) => setTimeout(r, 1000));
        window.scrollTo(0, 0);

        const response = await fetch(`/post/gptchat/`, {
            method: `POST`,
            signal: window.controller.signal,
            headers: {
                "content-type": `application/json`,
                accept: `text/event-stream`,
            },
            body: JSON.stringify({
                conversation_id: window.conversation_id,
                action: `_ask`,
                model: model.options[model.selectedIndex].value,
                jailbreak: jailbreak.options[jailbreak.selectedIndex].value,
                meta: {
                    id: window.token,
                    content: {
                        conversation: await get_conversation(window.conversation_id),
                        internet_access: document.getElementById("switch").checked,
                        uploaded_images: uploadedImages,
                        content_type: "text",
                        parts: [
                            {
                                content: message,
                                role: "user",
                            },
                        ],
                    },
                },
            }),
        });

        const reader = response.body.getReader();

        while (true) {
            const {value, done} = await reader.read();
            if (done) break;

            chunk = new TextDecoder().decode(value);

            if (
                chunk.includes(
                    `<form id="challenge-form" action="/backend-api/v2/conversation?`
                )
            ) {
                chunk = `cloudflare token expired, please refresh the page.`;
            }

            text += chunk;

            // const objects         = chunk.match(/({.+?})/g);

            // try { if (JSON.parse(objects[0]).success === false) throw new Error(JSON.parse(objects[0]).error) } catch (e) {}

            // objects.forEach((object) => {
            //     console.log(object)
            //     try { text += h2a(JSON.parse(object).content) } catch(t) { console.log(t); throw new Error(t)}
            // });

            document.getElementById(`gpt_${window.token}`).innerHTML =
                markdown.render(text);
            document.querySelectorAll(`code`).forEach((el) => {
                hljs.highlightElement(el);
            });

            window.scrollTo(0, 0);
            message_box.scrollTo({top: message_box.scrollHeight, behavior: "auto"});
        }  // 流传输结束

        // if text contains :
        if (
            text.includes(
                `instead. Maintaining this website and API costs a lot of money`
            )
        ) {
            document.getElementById(`gpt_${window.token}`).innerHTML =
                "An error occured, please reload / refresh cache and try again.";
        }
        // 保存信息
        if (uploadedImages.length > 0) {
            add_message(window.conversation_id, "user", message, uploadedImages);
        } else {
            add_message(window.conversation_id, "user", message);
        }
        //清空图片缓存
        clearGPTImage();
        add_message(window.conversation_id, "assistant", text);


        //入数据库
        message_box.scrollTop = message_box.scrollHeight;
        await remove_cancel_button();
        prompt_lock = false;

        await load_conversations(20, 0);
        window.scrollTo(0, 0);
        document.querySelector('.upload-icon').classList.remove('disabled-upload'); // 启用按钮

    } catch (e) {
        add_message(window.conversation_id, "user", message);

        message_box.scrollTop = message_box.scrollHeight;
        await remove_cancel_button();
        prompt_lock = false;

        await load_conversations(20, 0);

        console.log(e);

        let cursorDiv = document.getElementById(`cursor`);
        if (cursorDiv) cursorDiv.parentNode.removeChild(cursorDiv);

        if (e.name != `AbortError`) {
            let error_message = `oops ! something went wrong, please try again / reload. [stacktrace in console]`;

            document.getElementById(`gpt_${window.token}`).innerHTML = error_message;
            add_message(window.conversation_id, "assistant", error_message);
        } else {
            document.getElementById(`gpt_${window.token}`).innerHTML += ` [终止对话 aborted]`;
            add_message(window.conversation_id, "assistant", text + ` [终止对话  aborted]`);
        }

        window.scrollTo(0, 0);
        document.querySelector('.upload-icon').classList.remove('disabled-upload'); // 启用按钮
    }
}; // end ask_gpt

function clearGPTImage()
{
    //清空图片缓存
    uploadedImages = [];
    const container = document.getElementById('image-preview-container');
    // 清空容器内部的HTML
    container.innerHTML = '';
    // 隐藏容器
    container.style.display = 'none';
}

const clear_conversations = async () => {
  const elements = box_conversations.childNodes;
  let index = elements.length;
  if (index > 0) {
    while (index--) {
      const element = elements[index];
      if (
        element.nodeType === Node.ELEMENT_NODE &&
        element.tagName.toLowerCase() !== `button`
      ) {
        box_conversations.removeChild(element);
      }
    }
  }
};

const clear_conversation = async () => {
  reinit();
  let messages = message_box.getElementsByTagName(`div`);
  while (messages.length > 0) {
    message_box.removeChild(messages[0]);
  }
   let cropperContainer = document.getElementById("image-cropper-container");
    // 如果不存在，则添加到 message_box
    if (!cropperContainer) {
        message_box.innerHTML += `
            <div id="image-cropper-container" style="display: none;">
                <div class="crop-buttons-container">
                    <button id="confirm-crop">确定</button>
                    <button id="cancel-crop">取消</button>
                </div>
                <img id="image-preview" src="" alt="Preview">
            </div>
        `;
    }
};

const show_option = async (conversation_id) => {
  const conv = document.getElementById(`conv-${conversation_id}`);
  const yes = document.getElementById(`yes-${conversation_id}`);
  const not = document.getElementById(`not-${conversation_id}`);

  conv.style.display = "none";
  yes.style.display = "block";
  not.style.display = "block"; 
}

const hide_option = async (conversation_id) => {
  const conv = document.getElementById(`conv-${conversation_id}`);
  const yes = document.getElementById(`yes-${conversation_id}`);
  const not = document.getElementById(`not-${conversation_id}`);

  conv.style.display = "block";
  yes.style.display = "none";
  not.style.display = "none"; 
}
const delete_conversation = async (conversation_id) => {

  // Remove from local storage regardless of login status
  localStorage.removeItem(`conversation:${conversation_id}`);

  // Remove the conversation element from the DOM
  const conversationElement = document.getElementById(`convo-${conversation_id}`);
  if (conversationElement) {
    conversationElement.remove();
  }

  // If the user is logged in, make a request to the server to delete the conversation
  if (await isUserLoggedIn()) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute("content");
    await fetch('/post/deletechat/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken // Make sure to include CSRF token for security
      },
      body: JSON.stringify({ conversation_id: conversation_id })
    });
  }

  // If the currently active conversation is the one being deleted, start a new conversation
  if (window.conversation_id === conversation_id) {
    await new_conversation();
  }

  // Reload the conversations
  await load_conversations(20, 0, true);
};

const set_conversation = async (conversation_id) => {
  // history.pushState({}, null, `/chat/${conversation_id}`);
  window.conversation_id = conversation_id;

  await clear_conversation();
  await load_conversation(conversation_id);
  await load_conversations(20, 0, true);
};

const new_conversation = async () => {
  // history.pushState({}, null, `/chat/`);
  window.conversation_id = uuid();

  clearGPTImage();
  await clear_conversation();
  await load_conversations(20, 0, true);

};

const load_conversation = async (conversation_id) => {
  reinit();
  let conversation = await JSON.parse(
    localStorage.getItem(`conversation:${conversation_id}`)
  );
  console.log(conversation, conversation_id);
  // 添加文件加载部分
  // 检查是否存在 image-cropper-container
    let cropperContainer = document.getElementById("image-cropper-container");
    // 如果不存在，则添加到 message_box
    if (!cropperContainer) {
        message_box.innerHTML += `
            <div id="image-cropper-container" style="display: none;">
                <div class="crop-buttons-container">
                    <button id="confirm-crop">确定</button>
                    <button id="cancel-crop">取消</button>
                </div>
                <img id="image-preview" src="" alt="Preview">
            </div>
        `;
    }

    for (const item of conversation.items) {
         // Start with an empty string for images
      let imagesHtml = '';

      // Check if imageUrl is a string and not an empty array representation
      if (typeof item.imageUrl === 'string' && item.imageUrl !== '') {
        // Replace single quotes with double quotes to prepare for parsing
        const correctedImageUrlString = item.imageUrl.replace(/'/g, '"');
        // Parse the string to an actual array
        item.imageUrl = JSON.parse(correctedImageUrlString);
      }

      // Now check if there are imageUrls after converting and create image elements
      if (Array.isArray(item.imageUrl) && item.imageUrl.length > 0) {
        imagesHtml = `<div class="images-container-message">` + item.imageUrl.map(imagePath => {
          // Ensure imagePath is a relative path
          return `<div class="image-wrapper"><img src="/media/${imagePath}" alt="Uploaded Image" class="image-preview-message"></div>`;
        }).join('') + `</div>`;
      }


    // Append message HTML with or without images
    message_box.innerHTML += `
        <div class="message">
            <div class="user">
                ${item.role == "assistant" ? gpt_image : user_image}
                ${
                  item.role == "assistant"
                    ? `<i class="fa-regular fa-phone-arrow-down-left"></i>`
                    : `<i class="fa-regular fa-phone-arrow-up-right"></i>`
                }
                
            </div>
            <div class="content">
                ${imagesHtml} <!-- Place images above the text content -->
                ${
                  item.role == "assistant"
                    ? markdown.render(item.content)
                    : item.content
                }
            </div>
        </div>
    `;
}



  document.querySelectorAll(`code`).forEach((el) => {
    hljs.highlightElement(el);
  });

  message_box.scrollTo({ top: message_box.scrollHeight, behavior: "smooth" });

  setTimeout(() => {
    message_box.scrollTop = message_box.scrollHeight;
  }, 500);
};

const get_conversation = async (conversation_id) => {
  let conversation = await JSON.parse(
    localStorage.getItem(`conversation:${conversation_id}`)
  );
  return conversation.items;
};

const add_conversation = async (conversation_id, title) => {
  if (localStorage.getItem(`conversation:${conversation_id}`) == null) {
    localStorage.setItem(
      `conversation:${conversation_id}`,
      JSON.stringify({
        id: conversation_id,
        title: title,
        items: [],
      })
    );
  }
};
// 后端add_conversation 和 add_message 合并
const add_message = async (conversation_id, role, content, imageUrls = []) => {
  // Fetch the existing conversation from local storage
  let conversation = JSON.parse(localStorage.getItem(`conversation:${conversation_id}`));
  //alert(imageUrls)
  // Create a new message object
    const newMessage = {
      role: role,
      content: content,
      // Only add imageUrl if it's not an empty array, otherwise omit it or set it to null
      ...(imageUrls.length > 0 && { imageUrl: imageUrls })
    }; //The spread operator ... is used with a conditional expression.

  // Push the new message to the conversation items array
  conversation.items.push(newMessage);

  // Save the updated conversation back to local storage
  localStorage.setItem(`conversation:${conversation_id}`, JSON.stringify(conversation));

  // Save to the database
  // Ensure your save_message_to_db function can handle the array of imageUrls
  await save_message_to_db(conversation_id, role, content,imageUrls);
};




async function save_message_to_db(conversation_id, sender, content,imageUrls=[]) {
    if (await isUserLoggedIn()) { // 确认用户已登录
        // 获取令牌
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute("content");

        const response = await fetch('/post/savechat/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                 'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                conversation_id: conversation_id,
                role: sender,
                content: content,
                imageUrl: imageUrls,
            })
        });

        localStorage.setItem('last_updated', getBeijingTime());
        return response.json();
    } else {
        console.log('User not logged in. Message not saved.');
        return null;
    }
}


// 流传输
const load_conversations = async (limit, offset, loader) => {
  reinit();

  // 添加文件加载部分
  message_box.innerHTML += `
    <div id="image-cropper-container" style="display: none;">
      <div class="crop-buttons-container">
        <button id="confirm-crop">确定</button>
        <button id="cancel-crop">取消</button>
      </div>
      <img id="image-preview" src="" alt="Preview">
    </div>`;

  let conversations = [];
  const TIME_TOLERANCE = 10 * 1000;  // 10 seconds in milliseconds

  if (await isUserLoggedIn()) {
    const response = await fetch('/post/loadchat/');
    const serverData = await response.json();
    const local_last_updated = new Date(localStorage.getItem('last_updated') || 0);
    const server_last_updated = new Date(serverData.last_updated);

    if ((server_last_updated - local_last_updated) > TIME_TOLERANCE) {
      for (let conversation of serverData.conversations) {
        localStorage.setItem(`conversation:${conversation.id}`, JSON.stringify(conversation));
        conversations.push(conversation);
      }
      localStorage.setItem('last_updated', server_last_updated);
    } else {
      for (let i = 0; i < localStorage.length; i++) {
        if (localStorage.key(i).startsWith("conversation:")) {
          let conversation = localStorage.getItem(localStorage.key(i));
          conversations.push(JSON.parse(conversation));
        }
      }
    }
  }
  else {
    // If the user is not authenticated, only use locally stored conversations
    for (let i = 0; i < localStorage.length; i++) {
      if (localStorage.key(i).startsWith("conversation:")) {
        let conversation = localStorage.getItem(localStorage.key(i));
        conversations.push(JSON.parse(conversation));
      }
    }
  }

  await clear_conversations();

  for (conversation of conversations) {
    box_conversations.innerHTML += `
      <div class="convo" id="convo-${conversation.id}">
        <div class="left" onclick="set_conversation('${conversation.id}')">
          🗨️ <span class="convo-title">${conversation.title}</span>
        </div>
        <span onclick="show_option('${conversation.id}')" id="conv-${conversation.id}">🗑️</span>
        <span onclick="delete_conversation('${conversation.id}')" id="yes-${conversation.id}" style="display:none;">✔️</span>
        <span onclick="hide_option('${conversation.id}')" id="not-${conversation.id}" style="display:none;">❌</span>
      </div>`;
 }

  document.querySelectorAll(`code`).forEach((el) => {
    hljs.highlightElement(el);
  });
};

document.getElementById(`cancelButton`).addEventListener(`click`, async () => {
  window.controller.abort();
  console.log(`aborted ${window.conversation_id}`);
});

function h2a(str1) {
  var hex = str1.toString();
  var str = "";

  for (var n = 0; n < hex.length; n += 2) {
    str += String.fromCharCode(parseInt(hex.substr(n, 2), 16));
  }

  return str;
}

const uuid = () => {
  return `xxxxxxxx-xxxx-4xxx-yxxx-${Date.now().toString(16)}`.replace(
    /[xy]/g,
    function (c) {
      var r = (Math.random() * 16) | 0,
        v = c == "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    }
  );
};

window.conversation_id = uuid();
const message_id = () => {
  random_bytes = (Math.floor(Math.random() * 1338377565) + 2956589730).toString(
    2
  );
  unix = Math.floor(Date.now() / 1000).toString(2);

  return BigInt(`0b${unix}${random_bytes}`).toString();
};

window.onload = async () => {
  load_settings_localstorage();

  conversations = 0;
  for (let i = 0; i < localStorage.length; i++) {
    if (localStorage.key(i).startsWith("conversation:")) {
      conversations += 1;
    }
  }

  if (conversations == 0) localStorage.clear();

  await setTimeout(() => {
    load_conversations(20, 0);
  }, 1);

  if (!window.location.href.endsWith(`#`)) {
    if (/\/chat\/.+/.test(window.location.href)) {
      await load_conversation(window.conversation_id);
    }
  }

message_input.addEventListener(`keydown`, async (evt) => {
    if (prompt_lock) return;
    if (evt.keyCode === 13 && !evt.shiftKey) {
        evt.preventDefault();
        console.log('pressed enter');
        await handle_ask();
    } else {
      message_input.style.removeProperty("height");
      message_input.style.height = message_input.scrollHeight + 4 + "px";
    }
  });

  send_button.addEventListener(`click`, async () => {
    console.log("clicked send");
    if (prompt_lock) return;
    await handle_ask();
  });

  register_settings_localstorage();
};

document.querySelector(".mobile-sidebar").addEventListener("click", (event) => {
  const sidebar = document.querySelector(".conversations");

  if (sidebar.classList.contains("shown")) {
    sidebar.classList.remove("shown");
    event.target.classList.remove("rotated");
  } else {
    sidebar.classList.add("shown");
    event.target.classList.add("rotated");
  }

  window.scrollTo(0, 0);
});

const register_settings_localstorage = async () => {
  settings_ids = ["switch", "model", "jailbreak"];
  settings_elements = settings_ids.map((id) => document.getElementById(id));
  settings_elements.map((element) =>
    element.addEventListener(`change`, async (event) => {
      switch (event.target.type) {
        case "checkbox":
          localStorage.setItem(event.target.id, event.target.checked);
          break;
        case "select-one":
          localStorage.setItem(event.target.id, event.target.selectedIndex);
          break;
        default:
          console.warn("Unresolved element type");
      }
    })
  );
};

const load_settings_localstorage = async () => {
  settings_ids = ["switch", "model", "jailbreak"];
  settings_elements = settings_ids.map((id) => document.getElementById(id));
  settings_elements.map((element) => {
    if (localStorage.getItem(element.id)) {
      switch (element.type) {
        case "checkbox":
          element.checked = localStorage.getItem(element.id) === "true";
          break;
        case "select-one":
          element.selectedIndex = parseInt(localStorage.getItem(element.id));
          break;
        default:
          console.warn("Unresolved element type");
      }
    }
  });
};

// Theme storage for recurring viewers
const storeTheme = function (theme) {
  localStorage.setItem("theme", theme);
};

// set theme when visitor returns
const setTheme = function () {
  const activeTheme = localStorage.getItem("theme");
  colorThemes.forEach((themeOption) => {
    if (themeOption.id === activeTheme) {
      themeOption.checked = true;
    }
  });
  // fallback for no :has() support
  document.documentElement.className = activeTheme;
};

colorThemes.forEach((themeOption) => {
  themeOption.addEventListener("click", () => {
    storeTheme(themeOption.id);
    // fallback for no :has() support
    document.documentElement.className = themeOption.id;
  });
});

document.onload = setTheme();

function getBeijingTime() {
    const beijingOffset = 8; // Beijing is UTC+8
    const d = new Date();
    const utc = d.getTime() + d.getTimezoneOffset() * 60000;
    const nd = new Date(utc + (3600000 * beijingOffset));
    return nd.toISOString();
}


