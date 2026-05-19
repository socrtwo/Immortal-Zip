import UIKit

class SceneDelegate: UIResponder, UIWindowSceneDelegate {

    var window: UIWindow?

    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {
        guard let windowScene = scene as? UIWindowScene else { return }
        window = UIWindow(windowScene: windowScene)
        window?.rootViewController = ViewController()
        window?.makeKeyAndVisible()

        // Handle file opened at launch
        if let urlContext = connectionOptions.urlContexts.first {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                if let vc = self.window?.rootViewController as? ViewController {
                    vc.handleIncomingFile(url: urlContext.url)
                }
            }
        }
    }

    func scene(_ scene: UIScene, openURLContexts URLContexts: Set<UIOpenURLContext>) {
        guard let url = URLContexts.first?.url else { return }
        if let vc = window?.rootViewController as? ViewController {
            vc.handleIncomingFile(url: url)
        }
    }
}
