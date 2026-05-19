import UIKit
import WebKit
import UniformTypeIdentifiers

class ViewController: UIViewController, WKUIDelegate, WKNavigationDelegate, WKScriptMessageHandler, UIDocumentPickerDelegate {

    private var webView: WKWebView!

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor(red: 0.071, green: 0.071, blue: 0.071, alpha: 1)
        setupWebView()
        loadApp()
    }

    override var preferredStatusBarStyle: UIStatusBarStyle { .lightContent }

    // MARK: - WebView Setup

    private func setupWebView() {
        let config = WKWebViewConfiguration()
        let cc     = WKUserContentController()
        cc.add(self, name: "saveFile")
        cc.add(self, name: "shareFile")
        cc.add(self, name: "showToast")
        cc.add(self, name: "pickFile")
        config.userContentController = cc
        config.preferences.setValue(true, forKey: "allowFileAccessFromFileURLs")

        webView = WKWebView(frame: .zero, configuration: config)
        webView.uiDelegate         = self
        webView.navigationDelegate = self
        webView.isOpaque           = false
        webView.backgroundColor    = UIColor(red: 0.071, green: 0.071, blue: 0.071, alpha: 1)
        webView.scrollView.backgroundColor = webView.backgroundColor
        webView.translatesAutoresizingMaskIntoConstraints = false

        view.addSubview(webView)
        NSLayoutConstraint.activate([
            webView.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            webView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            webView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            webView.bottomAnchor.constraint(equalTo: view.bottomAnchor)
        ])
    }

    private func loadApp() {
        guard let htmlPath = Bundle.main.path(forResource: "immortal-unzip", ofType: "html") else {
            print("ERROR: immortal-unzip.html not found in bundle")
            return
        }
        let htmlURL = URL(fileURLWithPath: htmlPath)
        webView.loadFileURL(htmlURL, allowingReadAccessTo: htmlURL.deletingLastPathComponent())
    }

    // MARK: - Incoming File Handling

    func handleIncomingFile(url: URL) {
        let accessing = url.startAccessingSecurityScopedResource()
        defer { if accessing { url.stopAccessingSecurityScopedResource() } }

        guard let data = try? Data(contentsOf: url) else { return }
        let fileName = url.lastPathComponent
        let base64   = data.base64EncodedString()
        let js = "loadFileFromiOS('\(escapeJS(fileName))', '\(base64)');"
        webView.evaluateJavaScript(js, completionHandler: nil)
    }

    // MARK: - WKScriptMessageHandler

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        switch message.name {
        case "saveFile":
            guard let body     = message.body as? [String: String],
                  let fileName = body["fileName"],
                  let base64   = body["data"],
                  let data     = Data(base64Encoded: base64) else { return }
            saveFile(data: data, fileName: fileName)

        case "shareFile":
            guard let body     = message.body as? [String: String],
                  let fileName = body["fileName"],
                  let base64   = body["data"],
                  let data     = Data(base64Encoded: base64) else { return }
            shareFile(data: data, fileName: fileName)

        case "showToast":
            if let msg = message.body as? String { showToast(msg) }

        case "pickFile":
            openFilePicker()

        default:
            break
        }
    }

    // MARK: - File Picker

    private func openFilePicker() {
        var types: [UTType] = [.zip]
        if let epub = UTType(filenameExtension: "epub") { types.append(epub) }
        if let docx = UTType(filenameExtension: "docx") { types.append(docx) }
        if let xlsx = UTType(filenameExtension: "xlsx") { types.append(xlsx) }
        if let pptx = UTType(filenameExtension: "pptx") { types.append(pptx) }
        let picker = UIDocumentPickerViewController(forOpeningContentTypes: types)
        picker.delegate = self
        picker.allowsMultipleSelection = false
        present(picker, animated: true)
    }

    func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
        guard let url = urls.first else { return }
        handleIncomingFile(url: url)
    }

    // MARK: - Save / Share

    private func saveFile(data: Data, fileName: String) {
        let tempURL = FileManager.default.temporaryDirectory.appendingPathComponent(fileName)
        try? data.write(to: tempURL)
        let picker = UIDocumentPickerViewController(forExporting: [tempURL], asCopy: true)
        picker.delegate = self
        present(picker, animated: true)
    }

    private func shareFile(data: Data, fileName: String) {
        let tempURL = FileManager.default.temporaryDirectory.appendingPathComponent(fileName)
        try? data.write(to: tempURL)
        let vc = UIActivityViewController(activityItems: [tempURL], applicationActivities: nil)
        vc.popoverPresentationController?.sourceView = view
        vc.popoverPresentationController?.sourceRect = CGRect(x: view.bounds.midX, y: view.bounds.midY, width: 0, height: 0)
        present(vc, animated: true)
    }

    // MARK: - Toast

    private func showToast(_ message: String) {
        let alert = UIAlertController(title: nil, message: message, preferredStyle: .alert)
        present(alert, animated: true)
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { alert.dismiss(animated: true) }
    }

    // MARK: - Utility

    private func escapeJS(_ s: String) -> String {
        s.replacingOccurrences(of: "\\", with: "\\\\")
         .replacingOccurrences(of: "'", with: "\\'")
         .replacingOccurrences(of: "\n", with: "\\n")
         .replacingOccurrences(of: "\r", with: "\\r")
    }
}
